# Purpose

集水域のデータセットを作成するためのツール

## Functions

- pit fill
- flow direction
  - D8
  - D16
- flow accumulation
- catchment area
- watershed boundary
- some evaluation func for catchment area

## Usage

### venv

#### windows

```sh
python -m venv .venv
./.venv/Scripts/activate
```

#### mac

```sh
python3 -m venv .venv
. .venv/bin/activate
```

#### pip

```sh
pip install --upgrade pip
pip install -r requirement.txt
```

### Local Run

```sh
cd research-basic-catchment-area-toolset
python3 src/make_catchment_area.py
```

## data source

### store in base_data

- e.g., digital elevation model

### arranged catchment area sample

|catchment area|watershed boundary|
|---|---|
|![catchment area](https://github.com/harukimine/readme-image-source/blob/main/research-basic-catchment-area-dataset-toolset/catchment-area.png?raw=true)|![watershed](https://github.com/harukimine/readme-image-source/blob/main/research-basic-catchment-area-dataset-toolset/watershed.png?raw=true)|
