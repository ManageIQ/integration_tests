def search(element, nested_list):
    """Util function to search for a given element with the nested list.
    Mainly useful when searching for the existence of a given element within the tree.

    Args:
        element: Element that needs to be searched
        nested_list: List within which the element is to be searched

    Returns:
        True: If the element exists within the nested list
        False: If the element doesn't exist
    """
    if not nested_list:
        return False
    elif nested_list[0] == element:
        return True
    elif isinstance(nested_list[0], list):
        return search(element, nested_list[0])
    else:
        return search(element, nested_list[1:])
    return False
