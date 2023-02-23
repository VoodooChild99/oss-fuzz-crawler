import os
import toml
import argparse
import requests

from pathlib import Path
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn
)


URL_TEMPLATE = "https://storage.googleapis.com/{0}-backup.clusterfuzz-external.appspot.com/corpus/libFuzzer/{1}/public.zip"

progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)

def log(msg):
    progress.console.log(msg)

class Crawler:
    def __init__(self, skip_existed, dir, max_retries, corpuses, task_id) -> None:
        self.skip_existed = skip_existed
        self.dir = dir
        self.local_corpus_path_template = dir + '/{0}/{1}-corpus.zip'
        self.local_corpus_dir_template = dir + '/{0}'
        self.max_retries = max_retries
        self.session = requests.Session()
        self.task_id = task_id
        with open(corpuses, 'r') as f:
            self.corpuses = toml.load(f)
        
    def __get_corpus(self, url, filepath):
        retry_num = -1
        while True:
            try:
                corpus = self.session.get(url, stream=True)
                if corpus.status_code != 200:
                    log("[x] Failed to download corpus {}: {}".format(self.cur_target, corpus.content))
                    return None
                progress.update(self.task_id, total=int(corpus.headers['content-length']))
                with open(filepath, 'wb') as f:
                    for data in corpus.iter_content(chunk_size=1024):
                        f.write(data)
                        progress.update(self.task_id, advance=len(data))
                log("[o] Downloaded corpus {}".format(self.cur_target))
                return
            except KeyboardInterrupt as KI:
                raise KeyboardInterrupt(KI)
            except Exception as err:
                retry_num += 1
                if (self.max_retries is not None) and (retry_num >= self.max_retries):
                    log("[x] Max retries exceeded when downloading corpus {}: {}".format(self.cur_target, err))
                    return None

    def __download_one(self, proj: str):
        local_corpus = Path(
            self.local_corpus_path_template.format(proj, self.cur_target))
        url = URL_TEMPLATE.format(proj, self.cur_target)

        if local_corpus.exists():
            if self.skip_existed:
                log("[*] Skipping corpus {}: already exist".format(self.cur_target))
                return
            else:
                self.__get_corpus(url, local_corpus)
        else:
            self.__get_corpus(url, local_corpus)

    def run(self):
        for proj in self.corpuses:
            local_corpus_dir = Path(
                self.local_corpus_dir_template.format(proj))
            if not local_corpus_dir.exists():
                os.mkdir(local_corpus_dir)
            for fuzzer in self.corpuses[proj]:
                self.cur_target = fuzzer
                if not fuzzer.startswith(proj + '_'):
                    self.cur_target = proj + '_' + fuzzer
                progress.update(self.task_id, filename=self.cur_target)
                self.__download_one(proj)
                progress.reset(self.task_id)


def __to_absolute_path(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError('path {} does not exist'.format(p))
    return str(p.resolve())

def __to_absolute_path_create_if_not_existed(path: str) -> str:
    p = Path(path)
    if not p.exists():
        os.mkdir(p)
    return str(p.resolve())


def __to_uint(num: str) -> int:
    try:
        int_num = int(num)
    except Exception as err:
        raise argparse.ArgumentTypeError(
            'Failed to parse max retries: {}'.format(err))
    if int_num < 0:
        raise argparse.ArgumentTypeError('max retries must not be negative')
    return int_num


def main(args):
    task_id = progress.add_task("download", filename="", start=True)
    c = Crawler(args.skip_existed, args.directory, args.max_retries, args.corpuses, task_id)
    try:
        c.run()
    except KeyboardInterrupt:
        print("[:)] bye")
    finally:
        progress.remove_task(task_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OSS-Fuzz Public Corpora Crawler")
    parser.add_argument('-s', "--skip-existed",
                        action="store_true",
                        help="Download corpuses only when it's not in local")
    parser.add_argument('-d', "--directory",
                        required=True,
                        type=__to_absolute_path_create_if_not_existed,
                        help="Directory where the corpuses are stored locally")
    parser.add_argument('-m', "--max-retries",
                        type=__to_uint,
                        help="Max retires when downloading corpuses, always retry if not specified")
    parser.add_argument('corpuses',
                        type=__to_absolute_path,
                        help="The TOML file containing corpuses to download")
    args = parser.parse_args()
    with progress:
        main(args)
