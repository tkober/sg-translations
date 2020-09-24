import platform

def main():
    result = [
        ('[ENTER]', ' Edit Translation '),
        ('[UP]', ' Scroll up '),
        ('[DOWN]', ' Scroll down '),
        ('[F]', ' Filter '),
        ('[C]', ' Clear Filter ')
    ]

    if platform.system() == 'Darwin':
        result.append(('[K]', ' Copy Key '))

    result.append(('[Q]', ' Quit '))
    return result

def filter():
    return [
        ('[ENTER]', ' Quit and save Filter '),
        ('[UP|DOWN]', ' Change Filter Criteria '),
        ('[ESC]', ' Quit and clear Filter ')
    ]