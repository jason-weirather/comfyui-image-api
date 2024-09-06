import subprocess
import os
import json
import random

import importlib.resources as pkg_resources

class ComfyRunner:
    def __init__(self, comfyui_path, output_directory):
        self.comfyui_path = comfyui_path
        self.output_directory = output_directory

        # Use a context manager to get the path to the extra_model_paths.yaml file
        with pkg_resources.path("comfyui_image_api.Templates", "extra_model_paths.yaml") as yaml_file_path:
            self.extra_model_paths = str(yaml_file_path)
        with pkg_resources.path("comfyui_image_api.Templates.Workflow_api_json", "flex-dev-simple.json") as json_file_path:
            self.model_config_path = str(json_file_path)
        print("Extra model paths:")
        print(self.extra_model_paths)



        # Disable that weird tracking thing
        result = subprocess.run(["comfy", "tracking","disable"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Print the output
        print("Output:")
        print(result.stdout)
        # Print any error messages
        if result.stderr:
            print("Error:")
            print(result.stderr)
        # Stop any currently running server
        result = subprocess.run(["comfy", "stop"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Print the output
        print("Output:")
        print(result.stdout)
        # Print any error messages
        if result.stderr:
            print("Error:")
            print(result.stderr)
        # Start a freshly running server
        cmd = ["comfy","--workspace",comfyui_path,"launch","--background","--",
               "--port","8188",
               "--extra-model-paths-config",self.extra_model_paths,
               "--output-directory","/home/x/Projects/2024_08_ComfyUI/output-comfyui"
              ]

        # Run the command and capture the output
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Print the output
        print("Output:")
        print(result.stdout)

        # Print any error messages
        if result.stderr:
            print("Error:")
            print(result.stderr)


    def generate_image(self, prompt, seed=None):
        if seed is None:
            seed = random.randint(0, 289135626765403)

        # Load the workflow template
        with open(self.model_config_path, 'rt') as f:
            workflow = json.load(f)

        workflow['31']['inputs']['seed'] = seed
        workflow['6']['inputs']['text'] = prompt

        temp_workflow_path = "Processing/_temp_api.json"
        with open(temp_workflow_path, 'wt') as f:
            f.write(json.dumps(workflow, indent=2))

        # Run ComfyUI with the workflow
        cmd = f"comfy run --workflow {temp_workflow_path} --wait".split()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.stderr:
            raise Exception(f"Error generating image: {result.stderr}")
        return result.stdout
