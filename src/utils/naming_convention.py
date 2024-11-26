def to_camel_case(snake_str):
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))


def to_lower_camel_case(snake_str):
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    camel_string = to_camel_case(snake_str)
    return snake_str[0].lower() + camel_string[1:]


def convert_dict_keys_to_lower_camel_case(dictionary):
    if isinstance(dictionary, list):
        return [convert_dict_keys_to_lower_camel_case(item) for item in dictionary]

    if not isinstance(dictionary, dict):
        return dictionary

    return {
        to_lower_camel_case(key)
        if isinstance(key, str)
        else key: convert_dict_keys_to_lower_camel_case(value)
        if isinstance(value, (dict, list))
        else value
        for key, value in dictionary.items()
    }
