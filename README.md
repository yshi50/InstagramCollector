# InstagramCollector
> **Version:** 0.1

## Introduction
InstagramCollector is a tool designed to collect data from public/private Instagram user profiles for **research and study purposes**.  
It integrates **YOLO** for face detection and **AntelopeV2** for face recognition.

---

## Configuration
Before running, edit the `.env` file.

## Installation
Run the following script to install dependencies:
```bash
python setup.py
```
Activate runtime envirement:
```bash
conda activate InstagramCollector
```

## Run
To start download:
```bash
python download.py
```

To detect and keep only target user:
```bash
python detect.py
python match.py
```