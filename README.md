# ComfyUI Image API

## For Black Forest Lab's `FLUX.1 [dev]` model

The motivation for this project is that ComfyUI provides excellent workflow management on GPUs with limited memory resources, and is capable of running the `fp8` version of `FLUX.1 [dev]` in less than 20GB of GPU memory, this package lets users with GPU cards leverage ComfyUI's software through an API server, and one that can be containerized. 

The **ComfyUI Image API** provides a REST API to generate images using Black Forest Lab's **`FLUX.1 [dev]`** model with a ComfyUI workflow. It allows you to submit jobs to a queue for image generation based on prompts and various settings. This API integrates **ComfyUI**, **comfy-cli**, and **Flask** to provide an easy-to-use endpoint for generating AI-generated images.

## Features

- Expose an HTTP API to generate images using the **Comfy-Org Flux.1-Dev fp8** model.
- Establish a job queue to handle multiple image generation requests sequentially.
- Limit the maximum size of the job queue to large backlogs of jobs.
- Option to query the server for status, including the current number of jobs in the queue, API version, and more.
- Packaged in a Docker container for convenient deployment

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Running the API Server](#running-the-api-server)
4. [API Endpoints](#api-endpoints)
   - [POST /generate](#post-generate)
   - [GET /status](#get-status)
5. [Configuration](#configuration)
6. [Examples](#examples)

---

## Requirements

1. Before running the ComfyUI Image API, ensure the following dependencies are installed on your system:
  - **Python 3.8+**
  - **PyTorch** with CUDA support (if you are using GPU-based image generation)
  - **ComfyUI**
  - **comfy-cli** (Within an offline/docker environment, the external network calls need to be disable as in [this fork](https://github.com/jason-weirather/comfy-cli/tree/fixhangbug/comfy_cli))
  - **Docker** (optional but recommended for containerized deployments)

2. Download the `fp8` **`FLUX.1 [dev]`** model file [`flux1-dev-fp8.safetensors`](https://huggingface.co/Comfy-Org/flux1-dev/blob/main/flux1-dev-fp8.safetensors) from Comfy-Org on huggingface.

---

## Installation

### Cloning the Repository

```bash
git clone https://github.com/jason-weirather/comfyui-image-api.git
cd comfyui-image-api
```

### Installing Dependencies

You can install dependencies using `pip` or avoid this by using a `Docker` container.

#### Option 2: Docker (Recommended)

1. Build the Docker image:

   ```bash
   docker build -t comfyui-image-api .
   ```

---

## Running the API Server

### Command-line Options

Run the API using `comfy-api`, a CLI script that allows you to configure the server:

```bash
comfy-api --model-path /path/to/your/model
```

| Option           | Description                                                                                            | Default                     |
|------------------|--------------------------------------------------------------------------------------------------------|-----------------------------|
| `--model-path`   | Path to the model you want to use (required).                                                          | N/A                         |
| `--host`         | The host to bind the API server to. You can override the default via `COMFYUI_IMAGE_API_DEFAULT_HOST`. | `127.0.0.1`                 |
| `--port`         | Port for the API server.                                                                               | `8888`                      |
| `--comfyui-path` | Path to the ComfyUI installation. You can override this via the `COMFYUI_PATH` environment variable.   | N/A                         |
| `--comfyui-host` | The host to bind the ComfyUI server to (for internal use).                                             | `127.0.0.1`                 |
| `--comfyui-port` | Port for the ComfyUI server (for internal use).                                                        | `8188`                      |
| `--output-path`  | Directory to save generated images. If not provided, a temporary directory will be created.            | Temporary directory created |
| `--max-queue`    | Maximum number of image generation requests allowed in the queue at one time.                          | `5`                         |

#### Example with Docker

You can also run the server via Docker:

```bash
docker run --rm --user $(id -u):$(id -g) \
  -v /path/to/models:/path/to/models  \
  -p 8888:8888 \
  --gpus all \
  vacation/comfyui-image-api:0.1.0 \
    --model-path /path/to/models/flux1-dev-fp8.safetensors
```

Where `/path/to/models` contains the [`flux1-dev-fp8.safetensors`](https://huggingface.co/Comfy-Org/flux1-dev/blob/main/flux1-dev-fp8.safetensors) model from Comfy-Org on huggingface.

---

## API Endpoints

### POST `/generate`

This endpoint is used to generate an image based on a text prompt and other optional parameters.

#### Request Payload Schema

| Field     | Type    | Required | Description                                                    |
|-----------|---------|----------|----------------------------------------------------------------|
| `prompt`  | string  | Yes      | Text prompt for generating the image.                          |
| `steps`   | integer | No       | Number of steps for processing the image. Default: 30.         |
| `seed`    | integer | No       | Random seed for generating the image. Randomized if not given. |
| `width`   | integer | No       | Width of the image in pixels. Default: 512.                    |
| `height`  | integer | No       | Height of the image in pixels. Default: 512.                   |
| `cfg`     | number  | No       | Classifier-free guidance scale. Default: 4.0.                  |
| `denoise` | number  | No       | Denoise strength. Default: 1.0.                                |

#### Example Request

```bash
curl -X POST http://localhost:8888/generate \
-H "Content-Type: application/json" \
-d '{
  "prompt": "A sunset over a mountain range",
  "steps": 50,
  "width": 512,
  "height": 512,
  "cfg": 7.5,
  "denoise": 0.8
}'
```

#### Example Response

```json
{
  "status": "success",
  "image": "base64_encoded_image_data_here"
}
```

### GET `/status`

This endpoint provides the current status of the server, including the version, max queue size, and current number of jobs in the queue.

#### Example Request

```bash
curl -X GET http://localhost:8888/status
```

#### Example Response

```json
{
  "public_configuration": {
    "api_version": "0.1.0",
    "max_queue_size": 5,
    "current_workflow": "Comfy-Org Flux.1-Dev fp8"
  },
  "job_queue": 2
}
```

---

## Configuration

You can configure several settings using environment variables or command-line options. For example:

- **`COMFYUI_IMAGE_API_DEFAULT_HOST`**: Overrides the default host for the API server.
- **`COMFYUI_PATH`**: Path to the ComfyUI installation.

Additionally, the server configuration (such as `max_queue_size`) is exposed via the `/status` endpoint.

---

## Examples

### Python Client Example

You can use Python's `requests` library to interact with the API. Below is an example:

```python
import requests
import json
import base64
from PIL import Image
from io import BytesIO

# Define the URL and payload
url = "http://localhost:8888/generate"
payload = {
    "prompt": "A futuristic cityscape with flying cars",
    "width": 512,
    "height": 512,
    "steps": 50,
    "cfg": 7.5
}

# Send the request
response = requests.post(url, json=payload)

# Handle the response
if response.status_code == 200:
    data = response.json()
    image_base64 = data['image']
    image_data = base64.b64decode(image_base64)
    
    # Display the image
    image = Image.open(BytesIO(image_data))
    image.show()
else:
    print(f"Failed to generate image: {response.status_code}")
```

---

### License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

Note, **`FLUX.1 [dev]`** has its own [LICENSE](https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md).

---

### Author

- **Jason Weirather** - [@jason-weirather](https://github.com/jason-weirather)

---

This draft provides a comprehensive overview of your API's functionality and usage. Feel free to edit it further based on any additional features or specifics that you would like to include!
