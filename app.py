import argparse
from pathlib import Path
from subprocess import run, PIPE, call
import json
import sys, tempfile, os

def findNthOccurrence(string, substring, n):
    parts= string.split(substring, n)
    if len(parts)<=n:
        return -1
    return len(string)-len(parts[-1])-len(substring)


def findNthOccurrenceFromBehind(string, substring, n):
    end = len(string)

    while n > 0:
        index = string.rfind(substring, 0, end)
        n = n-1
        end = index
        if index == -1:
            break

    return index

def readTranslations(translationsDirectory, pattern='*.properties.ts', languagTag=lambda filename: filename.split('.')[0], blockLevel=2):
    files = { languagTag(f.name): f for f in Path(translationsDirectory).rglob(pattern) }
    languages = list(files.keys())

    result = []

    for language in languages:
        file = open(files[language], 'r')
        content = file.read()
        file.close()

        begin = findNthOccurrence(content, '{', blockLevel)
        end = findNthOccurrenceFromBehind(content, '}', blockLevel) + 1;

        functionContent = content[begin:end]
        functionContent = 'getJson = function() {}; console.log(JSON.stringify(getJson()));'.format(functionContent)

        p = run(['node'], stdout=PIPE, input=functionContent.encode('utf-8'))
        jsonString = p.stdout.decode('utf-8')
        translationJson = json.loads(jsonString)

        result.append((language, files[language], translationJson))

    return result

def buildTranslationsDictionary(translations):
    result = {}
    for locale, _, jsonObject in translations:
        for key in jsonObject.keys():
            if key in result:
                result[key][locale] = jsonObject[key]
            else:
                result[key] = { locale: jsonObject[key] }

    return result

def buildEditorContent(entry, allLanguages):
    completeEntry = {}
    for lang in allLanguages:
        translation = entry[lang] if lang in entry else None
        completeEntry[lang] = translation

    items = ['\t{}: {}'.format(key.__repr__(), value.__repr__()) for key, value in completeEntry.items()]
    itemsFormatted = ',\n'.join(items)
    result = '{\n' + itemsFormatted + '\n}'

    return result

def openEditor(key, dictionary, allLanguages):
    entry = dictionary[key]
    editorContent = buildEditorContent(entry, allLanguages)

    EDITOR = os.environ.get('EDITOR', 'vim')
    with tempfile.NamedTemporaryFile(suffix='.tmp', mode='w+') as tf:
        tf.write(editorContent)
        tf.flush()
        call([EDITOR, '+set backupcopy=yes', tf.name])

        tf.seek(0)
        updatedContent = tf.read()
        changed = updatedContent != editorContent

        print(changed)

def main():
    argparser = argparse.ArgumentParser(
        prog='translations',
        description='Saves you from touching these messy translation files in just-hire-angular.'
    )
    argparser.add_argument(
        'KEY', nargs="?",
        help='The key that shall be edited or created. If no key is provided all available translations will be listed.')
    args = argparser.parse_args()

    translationsDirectory = '/Users/kober/code/java/taloom/just-hire-angular/src/app/commons/provider/translation/resources';
    translations = readTranslations(translationsDirectory)
    dictionary = buildTranslationsDictionary(translations)
    allLanguages = [ l for l, _, _ in translations ]
    allLanguages.sort()

    if args.KEY is not None and args.KEY in dictionary:
        openEditor(args.KEY, dictionary, allLanguages)
    else:
        print("List is not yet implemented!")


if __name__ == '__main__':
    main()