# Jetson Virtual Touchpanel Tool

This tool enables Jetson to be controlled by hand gesture in air using a webcam and [`trt_pose`](https://github.com/NVIDIA-AI-IOT/trt_pose) as a backbone to do the AI handpose recognition.

![](/docs/images/vtouch_trtpose_start_notification.png)

## Dependencies

```
sudo apt-get update
sudo apt-get install -y python3-pip
pip3 install pyzmq pynput
```

## How to use

Start the indicator tool (and mouse control logic, which is not implemented yet).

```
cd virtual_touchpanel
python3 vtouch_indicator.py
```

You can start a dummy publish to act as trt_pose backend.

```
python3 dummy_trtpose_pub.py
```

