from importlib.metadata import PathDistribution, distribution
import reprlib

from packaging.requirements import Requirement

import external_dist


class MyRepr(reprlib.Repr):
    def repr_PathDistribution(self, dist: PathDistribution, level: int) -> str:
        return f"PathDistribution({dist._path!r})"


mrepr = MyRepr()

with external_dist.configure_finder(
    install_to_meta_path=True, options=external_dist.Options(include_prereleases=True)
):
    starlite = distribution("starlite")
    for r in map(Requirement, starlite.requires or []):
        dist = distribution(r.name)
        print(mrepr.repr(dist))
