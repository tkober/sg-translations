import argparse

def main():
    argparser = argparse.ArgumentParser(
        prog="translations",
        description='Saves you from touching these messy translation files in just-hire-angular.'
    )
    argparser.add_argument(
        'KEY', nargs="?",
        help='The key that shall be edited or created. If no key is provided all available translations will be listed.')
    args = argparser.parse_args()

if __name__ == '__main__':
    main()