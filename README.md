# Creative Robotic Assistant

This project explores creative robotics using the xArm platform, combining AI-driven generation, computer vision, and robotic control to enable a robot arm to autonomously create physical sketches. The system integrates generative models with perception and motion planning pipelines, translating abstract visual outputs into executable robot trajectories through iterative experimentation and refinement.

Developed by Harry Martens at the Human-Robot Interaction Lab at UNSW as part of his undergraduate engineering thesis and continuous work as a research assistant.

## Features
- Text-to-image drawing: `generate` a prompt and trace it on the canvas.
- Edit-in-place: `edit` the current drawing with a new prompt.
- Draw from file: `draw` an existing image.
- Canvas management: `erase` and `capture` snapshots.
- Robot safety helpers: basic error handling, speed profiles, and docking/centering moves.
- Fancy startup banner (uses `pyfiglet` if installed).

## Requirements
- Python 3.12 (matches `.pyenv` version used here).
- xArm robot reachable on your network (default IP `192.168.1.239`, configurable in `config/robot_config.py`).
- Camera supported by OpenCV (default index `0`).
- OpenAI API key available in your environment (`OPENAI_API_KEY`).

## Quickstart
```bash
# From the project root
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install openai opencv-python numpy scipy pyfiglet yaspin xarm-python-sdk pillow pupil_apriltags

# Run interactively (shows command menu)
python main.py

# Or run a one-off generate
python main.py --action generate --prompt "a robot sketching a skyline"
```

## Usage (interactive)
When started without CLI flags, you'll see the command menu. Available actions:
- `generate <prompt>`: imagine an image and draw it
- `edit <prompt>`: tweak the current canvas with a prompt
- `draw <image_path>`: trace an existing image file
- `erase`: clear the canvas
- `capture [save_path]`: snapshot the current canvas to a file (optional path)
- `errors`: print recent robot error summary
- `quit`: exit the program

## Configuration
- Robot: `config/robot_config.py` (IP address, speeds, tool Z heights, dock/center positions).
- Canvas: `config/canvas_config.py` (canvas bounds, dimensions).
- AI: `config/ai_config.py` (Image Generation model names, size, quality).
- Camera: `config/camera_config.py` (camera index, warmup, save location).

Adjust these files to match your robot setup, tool attachments, and workspace dimensions.

## How it works
- `main.py` wires services and exposes CLI/interactive loops.
- `src/services/*` split responsibilities: image generation (OpenAI), image processing, path planning, movement, robot control (`RobotService`), and camera capture.
- `tools/drawing_tool.py` coordinates drawing/erasing/capture flows across services.
- `core/models.py` defines enums for attachments, speeds, and robot states.

## Safety notes
- Keep the workspace clear and verify `config/canvas_config.py` bounds before running.
- Start with `SpeedType.SLOW` while testing new tools or poses.
- Use `errors` in interactive mode to review robot status; the system attempts limited auto-recovery but may require manual intervention.

## Troubleshooting
- Missing banner? Install `pyfiglet` (optional).
- OpenAI errors: ensure `OPENAI_API_KEY` is set and you have network access.
- Robot connection issues: confirm the IP in `config/robot_config.py` and that the xArm is reachable/powered.
- Camera read failures: adjust `camera_index` in `config/camera_config.py` and verify permissions.
