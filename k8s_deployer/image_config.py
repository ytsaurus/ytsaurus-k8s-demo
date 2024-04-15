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
    "grafana": ImageEntry(img="grafana/grafana", tag="9.5.3"),
    "datalens_control_api": ImageEntry(img="datalens-tech/datalens-control-api", tag="0.2038.1"),
    "datalens_data_api": ImageEntry(img="datalens-tech/datalens-data-api", tag="0.2038.1"),
    "datalens_ui": ImageEntry(img="datalens-tech/datalens-ui", tag="0.955.0"),
    "datalens_us": ImageEntry(img="datalens-tech/datalens-us", tag="0.116.0"),
    "datalens_pg_dump": ImageEntry(img="custom/datalens-pg-dump", tag="0.0.1"),
    "postgres": ImageEntry(img="postgres", tag="13-alpine"),
}
