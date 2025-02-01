string = "The car with the lowest mileage is a 2018 Chevrolet 1500 with 6,654 miles. \n\n"

word_buffer = string.replace("\r\n", "<br/>").replace("\n\n", "<br/>").replace("\n", "<br/>")

print(word_buffer)
