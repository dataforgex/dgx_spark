# FPS Game

A GPU-accelerated first-person shooter built with Godot 4.

## Requirements

- [Godot 4.2+](https://godotengine.org/download/) (use the standard version, not .NET)

## How to Run

1. Download and install Godot 4.2 or later
2. Open Godot and click "Import"
3. Navigate to this folder and select `project.godot`
4. Click "Import & Edit"
5. Press F5 or click the Play button to run the game

## Controls

| Key | Action |
|-----|--------|
| W/A/S/D | Move |
| Mouse | Look around |
| Left Click | Shoot |
| R | Reload |
| Space | Jump |
| ESC | Release mouse cursor |

## Features

- GPU-accelerated rendering (Vulkan/OpenGL via Forward+)
- First-person shooter mechanics
- Enemy AI that chases and attacks
- Ammo and reload system
- Health system
- Score tracking
- Dynamic enemy spawning
- Hit effects and muzzle flash
- Volumetric fog and ambient lighting

## GPU Rendering

The game uses Godot's Forward+ renderer which leverages:
- Vulkan (primary) or OpenGL fallback
- MSAA anti-aliasing
- SSAO (Screen Space Ambient Occlusion)
- SSIL (Screen Space Indirect Lighting)
- Volumetric fog
- Real-time shadows

## Quick Install (Linux)

```bash
# Download Godot 4.2
wget https://github.com/godotengine/godot/releases/download/4.2.2-stable/Godot_v4.2.2-stable_linux.x86_64.zip
unzip Godot_v4.2.2-stable_linux.x86_64.zip
./Godot_v4.2.2-stable_linux.x86_64 --path /home/dan/danProjects/dgx_spark/fps-game
```
