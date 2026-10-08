"""compare-shadow tests. No network, no git: the watch log is an inline string.

Run: python3 scripts/jev/test_compare_shadow.py
"""

import importlib.util
import pathlib
import sys
import unittest

_spec = importlib.util.spec_from_file_location(
    "compare_shadow", pathlib.Path(__file__).parent / "compare-shadow.py")
compare_shadow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_shadow)

SIGNAL = "https://garymarcus.substack.com/p/coming-soon-new-york-citys-hearing"
SUMMARY = "https://stratechery.com/2026/an-interview-with-jason-del-rey-about-muse-amazon-and-walmart/"
DISCARDED = "https://example.com/p/discarded-hype-piece"

LOG = f"""### Added 2026-10-05 (Weekly Tier 2 scan)

#### NYC hearing on AI risks

**Source:** Gary Marcus, ["Coming soon: New York City's hearing on AI risks"]({SIGNAL}), Substack, October 5, 2026

#### Scan summary

- **Sources scanned:**
  - [Stratechery (Ben Thompson)](https://stratechery.com/) - 1 in-window article (["An Interview with Jason Del Rey," Oct 1]({SUMMARY}))

## Discarded Signals

- [A hype piece]({DISCARDED}) - not structural
"""


class SectionUrls(unittest.TestCase):
    def test_only_source_line_links_count_as_citations(self):
        self.assertEqual(compare_shadow._section_urls(LOG, "2026-10-05"),
                         {compare_shadow.norm(SIGNAL)})


if __name__ == "__main__":
    unittest.main()
