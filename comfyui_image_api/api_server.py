from flask import Flask, request, jsonify
from comfyui_image_api.comfy_runner import ComfyRunner
import click
import os
import tempfile
import time
import base64
import shutil
import atexit
import random
import json
from jsonschema import validate, ValidationError
import importlib.resources as pkg_resources
from threading import Lock, Thread
import subprocess

from comfyui_image_api import __version__

app = Flask(__name__)

# Initialize queue and lock
job_queue = []
queue_lock = Lock()


class PublicServerConfig:
    def __init__(self, max_queue, workflow_name, comfyui_path):
        self.max_queue = max_queue
        self.workflow_name = workflow_name
        self.comfyui_path = comfyui_path
        self.__version__ = __version__

    def get_status_info(self):
        """Returns a dictionary with the server's public status details."""
        return {
            "api_version": self.__version__,
            "max_queue_size": self.max_queue,
            "current_workflow": self.workflow_name
        }

@click.command()
@click.option("--model-path", help="The path to your locally available model.", required=True)
@click.option("--host", default=os.environ.get("COMFYUI_IMAGE_API_DEFAULT_HOST","127.0.0.1"), help="The host to bind the api server to, the default can be overriden by the environment variable COMFYUI_IMAGE_API_DEFAULT_HOST", show_default=True)
@click.option("--port", default=8888, help="The port to bind the api server to.", show_default=True)
@click.option("--comfyui-path", default=os.environ.get("COMFYUI_PATH"), help="The path to the ComfyUI installation, the default can be overriden by COMFYUI_PATH", show_default=True)
@click.option("--comfyui-host", default="127.0.0.1", help="The host to bind the ComfyUI server to.", show_default=True)
@click.option("--comfyui-port", default=8188, help="The port to bind the ComfyUI server to.", show_default=True)
@click.option("--output-path", help="The path to write images, if not set, a temporary directory will be created.")
@click.option("--max-queue", default=5, help="Maximum number of image generation requests allowed in the queue.", show_default=True)
def main(model_path, host, port, comfyui_path, comfyui_host, comfyui_port, output_path, max_queue):

    if comfyui_path is None:
        raise click.UsageError("You must provide the --comfyui-path option or set the COMFYUI_PATH environment variable.")

    if output_path is None:
        temp_dir = tempfile.mkdtemp(prefix="my_temp_dir_")
        print(f"Temporary directory created at: {temp_dir}")
        output_path = temp_dir
        atexit.register(shutil.rmtree, temp_dir)

    config = PublicServerConfig(
        max_queue = max_queue,
        workflow_name = "Comfy-Org Flux.1-Dev fp8",
        comfyui_path = comfyui_path
    )
    app.config['public_config'] = config

    app.config['output_path'] = output_path

    app.config['comfy_runner'] = ComfyRunner(
        comfyui_path=comfyui_path,
        comfyui_host=comfyui_host,
        comfyui_port=comfyui_port,
        model_path=model_path,
        output_directory=output_path
    )
    print(f"ComfyRunner output directory: {app.config['output_path']}")

    """Run the ComfyUI Image API server."""
    app.run(host=host, port=port)

@app.route("/status", methods=["GET"])
def status():
    config = app.config['public_config']

    return jsonify({
        "public_configuration": config.get_status_info(),
        "job_queue": len(job_queue)
    }), 200

# Pull the generate json schema to validate against
with pkg_resources.path("comfyui_image_api.Schema", "generate_schema.json") as json_path:
    generate_schema = json.loads(open(json_path).read())

# Add a lock object to control generation
generation_lock = Lock()

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    try:
        # Validate the incoming data against the schema
        validate(instance=data, schema=generate_schema)
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.message}), 400

    # Seed requires more complicated processing
    if data.get("seed") is None:
        seed = random.randint(
            generate_schema["properties"]["seed"]["minimum"],
            generate_schema["properties"]["seed"]["maximum"]
        )
    else:
        seed = data.get("seed")

    processed_data = {
        "prompt": data.get("prompt", ""),
        "seed": seed,
        "width": data.get("width", generate_schema["properties"]["width"]["default"]),
        "height": data.get("height", generate_schema["properties"]["height"]["default"]),
        "steps": data.get("steps", generate_schema["properties"]["steps"]["default"]),
        "cfg": data.get("cfg", generate_schema["properties"]["cfg"]["default"]),
        "denoise": data.get("denoise", generate_schema["properties"]["denoise"]["default"])
    }

    # Lock queue operations
    with queue_lock:
        # Check if the queue is full
        if len(job_queue) >= app.config['public_config'].max_queue:
            return jsonify({"status": "error", "message": "Job queue is full. Please try again later."}), 429

        # Add job to the queue
        job_queue.append(processed_data)

    # Process the job synchronously
    return process_job(processed_data)

def process_job(data):
    comfy_runner = app.config['comfy_runner']
    output_path = app.config['output_path']

    print(f"Output path: {output_path}")

    try:
        # Locking ensures only one job runs at a time
        with generation_lock:
            # Generate the image
            comfy_runner.generate_image(data)

            # Poll the output directory for the new image
            image_path = None

            for _ in range(20):  # Try for up to 20 seconds
                time.sleep(1)  # Wait 1 second between checks

                # Get the list of files in the directory
                files = sorted(os.listdir(output_path), key=lambda x: os.path.getctime(os.path.join(output_path, x)))

                if files:
                    image_path = os.path.join(output_path, files[-1])  # Get the most recently created file
                    print(f"Detected new file: {image_path}")

                    # Ensure the file is fully written (small delay)
                    time.sleep(1)
                    break

            if not image_path:
                raise Exception("Image not generated in time.")

            # Read the image and encode it in base64
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            # Remove the job from the queue
            with queue_lock:
                job_queue.remove(data)

            # Return the base64-encoded image in the response
            return jsonify({"status": "success", "image": encoded_string}), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    main()
