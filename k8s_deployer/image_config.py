from dataclasses import dataclass

repo = "cr.yandex/crpgg53svilvkn982otu"


@dataclass
class ImageEntry:
    img: str
    tag: str

    def __str__(self):
        return f"{repo}/{self.img}:{self.tag}"


images = {
    "core": ImageEntry(
        img="ytsaurus/ytsaurus",
        tag="stable-23.2.0-relwithdebinfo",
    ),
    "ui": ImageEntry(
        img="ytsaurus/ui",
        tag="1.22.3",
    ),
    "jupyter": ImageEntry(
        img="ytsaurus/jupyter-tutorial",
        tag="0.0.31-datalens-intro",
    ),
    "demo_data": ImageEntry(
        img="ytsaurus/demo_data",
        tag="0.0.13-with-datalens2",
    ),
    "strawberry": ImageEntry(img="ytsaurus/strawberry", tag="0.0.11"),
    "spyt": ImageEntry(
        img="ytsaurus/spyt",
        tag="1.77.0",
    ),
    "chyt": ImageEntry(
        img="ytsaurus/chyt",
        tag="2.14.0-relwithdebinfo",
    ),
    "queryTracker": ImageEntry(
        img="ytsaurus/query-tracker",
        tag="0.0.5-ya-build-relwithdebinfo",
    ),
}
