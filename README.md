# OSS-Fuzz Public Corpora Crawler
This tool downloads corpora published by [OSS-Fuzz](https://github.com/google/oss-fuzz).

The code was tested with `Python 3.8.16` under `Ubuntu 20.04`.

Contributions are welcomed :)

## Usage
1. get the code
```shell
git clone https://github.com/VoodooChild99/oss-fuzz-crawler.git
```

2. install dependencies
```shell
pip install -r requirements.txt
```

3. run `crawler.py`
```shell
usage: crawler.py [-h] [-s] -d DIRECTORY [-m MAX_RETRIES] corpuses

OSS-Fuzz Public Corpora Crawler

positional arguments:
  corpuses              The TOML file containing corpuses to download

optional arguments:
  -h, --help            show this help message and exit
  -s, --skip-check      Download corpuses only when it's not in local, hash checks are skipped
  -d DIRECTORY, --directory DIRECTORY
                        Directory where the corpuses are stored
  -m MAX_RETRIES, --max-retries MAX_RETRIES
                        Max retires when downloading corpuses, always retry if not specified
```

## Target Corpora
[corpora.toml](./corpora.toml) already covers several [OSS-Fuzz](https://github.com/google/oss-fuzz) projects used by [FuzzBench](https://github.com/google/fuzzbench).

You can add more corpus by adding stuff into [corpora.toml](./corpora.toml) as follows:
```toml
project = [ "target1", "target2", .. ]
```

