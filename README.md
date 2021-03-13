# Jetson Virtual Touchpanel Tool

This tool enables Jetson to be controlled by hand gesture in air using a webcam and [`trt_pose`](https://github.com/NVIDIA-AI-IOT/trt_pose) as a backbone to do the AI handpose recognition.

![](/docs/images/vtouch_trtpose_start_notification.png)

It is primarily desigend for interactive signage systems.<br> 
By utilizing a camera and AI to understand the users handpose in front of the screen, it enables users to interact with the system without physically touching the touchpanel or ohter input devices like a mouse.

## Dependencies

```
sudo apt-get update
sudo apt-get install -y python3-pip
pip3 install pyzmq pynput
```

## Download models

Save the following trt_pose model under `~/jetson_virtual_touchpanel/pub/model`.

| Model | Class | Trained with | Download |
|--------|-----------------|----------------|--------|
| trt_pose model | `hand` | 2600 images | [handpose_resnet18_att_224x224_nvhand-2k6_trt.pth](https://drive.google.com/file/d/1ALFjVq8gfE0tcvtHuMpu0Qsi_oSRfkWw/view?usp=sharing) |


Save the following SVM model (for gesture classification) under `~/jetson_virtual_touchpanel/pub/model`.

| Model | Class | Trained with | Download |
|--------|-----------------|----------------|--------|
| SVM model | `no-hand`, `pan`, `point`, `click`, `(other)` | 200 images | [svmmodel_5class.sav](https://drive.google.com/file/d/1AO-wU5ftYy6SEhoJurCMX5NKDW-0HF2Z/view?usp=sharing) |



## Install jetson-pose-container

```
cd
git clone https://github.com/tokk-nv/jetson-pose-container
cd jetson-pose-container
./scripts/set_nvidia_runtime.sh
./scripts/copy-jetson-ota-key.sh
./build.sh
```

## How to use

### Physical setup

- Plug USB webcam to Jetson NX.

### Command

Start the Jetson Virtual Touchpanel by invoking the indicator script.

```
cd virtual_touchpanel
python3 vtouch_indicator.py
```

Then from its menu, select "Start camera-pose service".

![](/docs/images/vtouch_menu_start.png)

