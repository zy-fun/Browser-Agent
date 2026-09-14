from browser.observation import build_observation


def test_build_observation_filters_and_formats_elements() -> None:
    raw = {
        "goal": "Find a product.",
        "url": "https://example.test/search",
        "open_pages_titles": ("Search",),
        "active_page_index": [0],
        "axtree_object": {
            "nodes": [
                {
                    "role": {"value": "checkbox"},
                    "name": {"value": "Include archived"},
                    "browsergym_id": "a11",
                    "properties": [
                        {"name": "checked", "value": {"value": "true"}},
                        {"name": "readonly", "value": {"value": True}},
                        {"name": "focusable", "value": {"value": True}},
                    ],
                },
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
            "a11": {"visibility": 1.0},
        },
    }

    observation = build_observation(raw)

    assert observation.title == "Search"
    assert observation.goal == "Find a product."
    assert [element.element_id for element in observation.elements] == ["a11", "a12", "a13"]
    assert observation.visible_text == ("Products",)
    assert "[a12] textbox 'Search'" in observation.to_text()
    assert (
        "[a11] checkbox 'Include archived' checked=true readonly=true" in observation.to_text()
    )


def test_control_state_changes_observation_identity() -> None:
    base_node = {
        "role": {"value": "checkbox"},
        "name": {"value": "Nb"},
        "browsergym_id": "21",
    }
    raw = {
        "goal": "Select Nb.",
        "url": "https://example.test",
        "axtree_object": {"nodes": [base_node]},
        "extra_element_properties": {"21": {"visibility": 1.0}},
    }
    unchecked = {
        **raw,
        "axtree_object": {
            "nodes": [
                {
                    **base_node,
                    "properties": [
                        {"name": "checked", "value": {"value": "false"}},
                    ],
                }
            ]
        },
    }
    checked = {
        **raw,
        "axtree_object": {
            "nodes": [
                {
                    **base_node,
                    "properties": [
                        {"name": "checked", "value": {"value": "true"}},
                    ],
                }
            ]
        },
    }

    unchecked_observation = build_observation(unchecked)
    checked_observation = build_observation(checked)

    assert unchecked_observation.elements[0].states == ("checked=false",)
    assert checked_observation.elements[0].states == ("checked=true",)
    assert unchecked_observation != checked_observation


def test_action_error_is_compacted_to_first_line() -> None:
    raw = {
        "goal": "Submit",
        "url": "https://example.test",
        "axtree_object": {"nodes": []},
        "last_action_error": "TimeoutError: not editable\nCall log:\nvery long detail",
    }

    observation = build_observation(raw)

    assert observation.last_action_error == "TimeoutError: not editable"
