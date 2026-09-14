from browser.observation import build_observation


def test_build_observation_filters_and_formats_elements() -> None:
    raw = {
        "url": "https://example.test/search",
        "open_pages_titles": ("Search",),
        "active_page_index": [0],
        "axtree_object": {
            "nodes": [
                {
                    "role": {"value": "textbox"},
                    "name": {"value": "Search"},
                    "browsergym_id": "a12",
                },
                {
                    "role": {"value": "button"},
                    "name": {"value": "Submit"},
                    "browsergym_id": "a13",
                },
                {"role": {"value": "StaticText"}, "name": {"value": "Products"}},
                {
                    "role": {"value": "button"},
                    "name": {"value": "Hidden"},
                    "browsergym_id": "a14",
                },
            ]
        },
        "extra_element_properties": {
            "a12": {"visibility": 1.0},
            "a13": {"visibility": 1.0},
            "a14": {"visibility": 0.0},
        },
    }

    observation = build_observation(raw)

    assert observation.title == "Search"
    assert [element.element_id for element in observation.elements] == ["a12", "a13"]
    assert observation.visible_text == ("Products",)
    assert "[a12] textbox 'Search'" in observation.to_text()
