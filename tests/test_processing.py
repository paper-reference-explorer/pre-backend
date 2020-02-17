import re

import hypothesis as hy
import hypothesis.strategies as st

from src import processing


alphanumeric_underscore_pattern = re.compile(r"[\w_]*")


@hy.given(st.text())
def test_clean_id(s: str) -> None:
    assert alphanumeric_underscore_pattern.match(processing.clean_id(s))


same_len_lists = st.integers(min_value=1, max_value=100).flatmap(
    lambda n: st.tuples(
        st.lists(
            st.lists(
                st.text(
                    alphabet=st.characters(whitelist_categories="L"),
                    min_size=1,
                    max_size=1,
                ),
                min_size=1,
                max_size=100,
            ),
            min_size=n,
            max_size=n,
        ),
        st.lists(
            st.text(alphabet=st.characters(whitelist_categories="L"), min_size=1),
            min_size=n,
            max_size=n,
        ),
    )
)


@hy.given(same_len_lists)
def test_clean_authors(authors):
    first_names, last_names = authors
    expected = " ".join([processing.stemmer.stem(n) for n in last_names])
    names = ",".join(
        [".".join(fn) + "." + ln for fn, ln in zip(first_names, last_names)]
    )
    then = processing.clean_authors(names)
    # print(expected, names, then)
    assert then == expected


if __name__ == "__main__":
    test_clean_authors(([["A"]], ["ª"]))
