import os
import hashlib
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


URL_TEMPLATE = "https://storage.googleapis.com/{0}-backup.clusterfuzz-external.appspot.com/corpus/libFuzzer/{0}_{1}/public.zip"

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
    def __init__(self, skip_check, dir, max_retries, corpuses) -> None:
        self.skip_check = skip_check
        self.dir = dir
        self.local_corpus_path_template = dir + '/{0}/{0}-{1}-corpus.zip'
        self.local_corpus_dir_template = dir + '/{0}'
        self.max_retries = max_retries
        self.session = requests.Session()
        with open(corpuses, 'r') as f:
            self.corpuses = toml.load(f)
        
    def __get_corpus(self, url):
        retry_num = -1
        with progress:
            task_id = progress.add_task(
                "download", filename=self.cur_target, start=True)
            while True:
                try:
                    corpus = self.session.get(url)
                    progress.update(task_id, total=int(
                        corpus.headers['content-length']))
                    all_data = b""
                    # progress.start_task(task_id)
                    for data in corpus.iter_content(chunk_size=1024):
                        all_data += data
                        progress.update(task_id, advance=len(data))
                    progress.remove_task(task_id)
                    if corpus.status_code != 200:
                        log("[x] Failed to download corpus {}: {}".format(self.cur_target, all_data))
                        return None
                    return all_data
                except KeyboardInterrupt as KI:
                    raise KeyboardInterrupt(KI)
                except Exception as err:
                    retry_num += 1
                    if (self.max_retries is not None) and (retry_num >= self.max_retries):
                        log("[x] Max retries exceeded when downloading corpus {}: {}".format(self.cur_target, err))
                        return None

    def __download_one(self, proj: str, target: str):
        local_corpus = Path(
            self.local_corpus_path_template.format(proj, target))
        self.cur_target = '{}-{}'.format(proj, target)
        url = URL_TEMPLATE.format(proj, target)

        if not self.skip_check:
            # check hash
            corpus = self.__get_corpus(url)
            if corpus is None:
                return
            new_hash = hashlib.sha256(corpus).hexdigest()
            if local_corpus.exists():
                with open(local_corpus, 'rb') as f:
                    old_hash = hashlib.sha256(f.read()).hexdigest()
                if new_hash == old_hash:
                    log("[*] Skipping corpus {}: already exist".format(self.cur_target))
                    return
                else:
                    with open(local_corpus, 'wb') as f:
                        f.write(corpus)
                        log("[o] Updated corpus {}".format(self.cur_target))
            else:
                with open(local_corpus, 'wb') as f:
                    f.write(corpus)
                    log("[o] Downloaded corpus {}".format(self.cur_target))
        else:
            # do not check, ignore if existed
            if local_corpus.exists():
                log("[*] Skipping corpus {}: already exist".format(self.cur_target))
                return
            else:
                corpus = self.__get_corpus(url)
                if corpus is None:
                    return
                with open(local_corpus, 'wb') as f:
                    f.write(corpus)
                    log("[o] Downloaded corpus {}".format(self.cur_target))

    def run(self):
        for proj in self.corpuses:
            local_corpus_dir = Path(
                self.local_corpus_dir_template.format(proj))
            if not local_corpus_dir.exists():
                os.mkdir(local_corpus_dir)
            for t in self.corpuses[proj]:
                self.__download_one(proj, t)


def __to_absolute_path(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError('path {} does not exist'.format(p))
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
    c = Crawler(args.skip_check, args.directory, args.max_retries, args.corpuses)
    try:
        c.run()
    except KeyboardInterrupt:
        print("[:)] bye")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OSS-Fuzz Public Corpora Crawler")
    parser.add_argument('-s', "--skip-check",
                        action="store_true",
                        help="Download corpuses only when it's not in local, hash checks are skipped")
    parser.add_argument('-d', "--directory",
                        required=True,
                        type=__to_absolute_path,
                        help="Directory where the corpuses are stored")
    parser.add_argument('-m', "--max-retries",
                        type=__to_uint,
                        help="Max retires when downloading corpuses, always retry if not specified")
    parser.add_argument('corpuses',
                        type=__to_absolute_path,
                        help="The TOML file containing corpuses to download")
    args = parser.parse_args()
    main(args)
