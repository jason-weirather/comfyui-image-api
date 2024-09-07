from flask import Flask, request, jsonify
from comfyui_image_api.comfy_runner import ComfyRunner
import click
import os
import tempfile
import time
import base64
import shutil
import atexit

app = Flask(__name__)

@click.command()
@click.option("--host", default="0.0.0.0", help="The host to bind the server to.", show_default=True)
@click.option("--port", default=8888, help="The port to bind the server to.", show_default=True)
@click.option("--comfyui-path", default=os.environ.get("COMFYUI_PATH"), help="The path to the ComfyUI installation.", show_default=True)
@click.option("--output-path", help="The path to write images.")
def main(host, port, comfyui_path, output_path):

    if comfyui_path is None:
        raise click.UsageError("You must provide the --comfyui-path option or set the COMFYUI_PATH environment variable.")

    if output_path is None:
        temp_dir = tempfile.mkdtemp(prefix="my_temp_dir_")
        print(f"Temporary directory created at: {temp_dir}")
        output_path = temp_dir
        atexit.register(shutil.rmtree, temp_dir)

    app.config['output_path'] = output_path

    app.config['comfy_runner'] = ComfyRunner(
        comfyui_path=comfyui_path,
        output_directory=output_path
    )
    print(f"ComfyRunner output directory: {app.config['output_path']}")

    """Run the ComfyUI Image API server."""
    app.run(host=host, port=port)


#import os
#import time
#import base64
#from flask import Flask, request, jsonify

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    prompt = data.get("prompt", "")
    seed = data.get("seed")

    comfy_runner = app.config['comfy_runner']
    output_path = app.config['output_path']
    print(f"Output path: {output_path}")

    try:
        # Generate the image
        comfy_runner.generate_image(prompt, seed)

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

        # Return the base64-encoded image in the response
        return jsonify({"status": "success", "image": encoded_string}), 200

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/generate2", methods=["POST"])
def generate2():
    data = request.json
    prompt = data.get("prompt", "")
    seed = data.get("seed")

    comfy_runner = app.config['comfy_runner']
    output_path = app.config['output_path']
    print(output_path)

    try:
        # Generate the image
        comfy_runner.generate_image(prompt, seed)

        # Poll the output directory for the new image
        image_path = None
        for _ in range(10):  # Try for up to 10 seconds
            time.sleep(1)  # Wait 1 second between checks
            files = sorted(os.listdir(output_path), key=lambda x: os.path.getctime(os.path.join(output_path, x)))
            print(files)
            if files:
                image_path = os.path.join(output_path, files[-1])  # Get the latest file
                break

        if not image_path:
            raise Exception("Image not generated in time.")

        # Read the image and encode it in base64
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        # Return the base64-encoded image in the response
        return jsonify({"status": "success", "image": encoded_string}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    main()
