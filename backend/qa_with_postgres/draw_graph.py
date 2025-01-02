string_list = [ "the", "table", '?",', '```', "sql", '":', '"', "There", "are", '"', 'answer', '":', "apple", "mangos"]

words_to_build = ['"answer":', '```sql']
input_str = ''


def format_to_openai_tool_messages(word, word_to_build, string_builder):
    string_builder += word
    if string_builder != word_to_build[:len(string_builder)]:
        string_builder = ''
    else:
        if string_builder == word_to_build:
            return string_builder
        return string_builder

for word_to_build in words_to_build:
    for word in string_list:
        if type(format_to_openai_tool_messages(word, word_to_build, input_str)) == str:
            print("String: ",format_to_openai_tool_messages(word, word_to_build, input_str))
            input_str = format_to_openai_tool_messages(word, word_to_build, input_str)
        if input_str == word_to_build:
            print("Final String: ", input_str)
            input_str = ''