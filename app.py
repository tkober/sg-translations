import argparse
from enum import Enum
from pathlib import Path
from subprocess import run, PIPE, call
import json
import tempfile, os
import ast
import re
import curses
from gupy.geometry import Padding
from gupy.screen import ConstrainedBasedScreen
from gupy.view import ListView, Label, HBox, BackgroundView
import keys
import legends

COLOR_PAIR_DEFAULT=0
COLOR_PAIR_TITLE=1
COLOR_PAIR_KEY=2
COLOR_PAIR_DESCRIPTION=3
COLOR_PAIR_PATTERN=4
COLOR_PAIR_SELECTED=5
COLOR_PAIR_ADDED=6
COLOR_PAIR_DELETED=7
COLOR_PAIR_MODIFIED=8
COLOR_PAIR_MOVED=9
COLOR_PAIR_UNTRACKED=10
COLOR_PAIR_STAGED=11
COLOR_PAIR_CONFIRMATION=12
COLOR_PAIR_CONFIRMATION_SELECTION=13

BLOCK_LEVEL = 2
TRANSLATION_DIRECTORY = '/Users/kober/code/java/taloom/just-hire-angular/src/app/commons/provider/translation/resources'
TRANSLATION_PATTERN = '*.properties.ts'

class Diff(Enum):
    ADDED = 1
    UPDATED = 2
    DELETED = 3

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

def readTranslations(translationsDirectory, pattern=TRANSLATION_PATTERN, languagTag=lambda filename: filename.split('.')[0], blockLevel=BLOCK_LEVEL):
    files = { languagTag(f.name): f for f in Path(translationsDirectory).rglob(pattern) }
    languages = list(files.keys())

    result = {}

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

        result[language] = (files[language], translationJson)

    return result

def buildTranslationsDictionary(translations):
    result = {}
    for locale, (_, jsonObject) in translations.items():
        for key in jsonObject.keys():
            if key in result:
                result[key][locale] = jsonObject[key]
            else:
                result[key] = { locale: jsonObject[key] }

    return result

def translationFromDictionary(key, dictionary):
    return dictionary[key] if key in dictionary else {}

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
    entry = translationFromDictionary(key, dictionary)
    editorContent = buildEditorContent(entry, allLanguages)

    EDITOR = os.environ.get('EDITOR', 'vim')
    with tempfile.NamedTemporaryFile(suffix='.tmp', mode='w+') as tf:
        tf.write(editorContent)
        tf.flush()
        call([EDITOR, '+set backupcopy=yes', tf.name])

        tf.seek(0)
        updatedContent = tf.read()
        updatedContent = updatedContent.strip()
        changed = updatedContent != editorContent

        return (changed, updatedContent)


def getDiff(old, new, allLanguages):
    result = []

    for lang in allLanguages:
        oldTranslation = old[lang] if lang in old else None
        newTranslation = new[lang] if lang in new else None

        if oldTranslation != newTranslation:

            if oldTranslation is None:
                result.append((lang, newTranslation, oldTranslation, Diff.ADDED))
            elif newTranslation is None:
                result.append((lang, newTranslation, oldTranslation, Diff.DELETED))
            else:
                result.append((lang, newTranslation, oldTranslation, Diff.UPDATED))

    return result

def applyDiff(key, diff, translations):
    for lang, newValue, oldValue, diffType in diff:
        file, _ = translations[lang]

        if Diff.ADDED == diffType:
            addTranslation(key, newValue, file)

        elif Diff.UPDATED == diffType:
            changeTranslationLine(file, key, newValue, oldValue)

        elif Diff.DELETED == diffType:
            changeTranslationLine(file, key, None, oldValue)

def buildTranslationLine(key, value, blockLevel, indentation='    '):
    return '\n{}{}: {},'.format(indentation*blockLevel, key.__repr__(), value.__repr__())

def buildUpdatePattern(key, value):
    KEY = key.__repr__()
    VALUE = value.__repr__()
    regex = r"\s*" + re.escape(KEY) + r"\s*[:]\s*" + re.escape(VALUE) + r"\s*,?\s*\n"

    return regex


def changeTranslationLine(filePath, key, newValue, oldValue):
    line = ''
    if newValue is not None:
        blockLevel = BLOCK_LEVEL + 1
        line = buildTranslationLine(key, newValue, blockLevel)
    line = line + '\n'

    updatePattern = buildUpdatePattern(key, oldValue)

    file = open(filePath, 'r')
    content = file.read()
    file.close()

    content = re.sub(updatePattern, line, content)
    file = open(filePath, 'w')
    file.write(content)
    file.close()

def addTranslation(key, value, filePath):
    blockLevel = BLOCK_LEVEL+1
    line = buildTranslationLine(key, value, blockLevel)

    file = open(filePath, 'r')
    content = file.read()
    file.close()

    index = findNthOccurrence(content, '{', blockLevel)
    index = index+1
    content = content[:index] + line + content[index:]

    file = open(filePath, 'w')
    file.write(content)
    file.close()


def updateTranslation(key, updatedTranslation, dictionary, allLanguages, translations):
    oldValues = translationFromDictionary(key, dictionary)
    newValues = ast.literal_eval(updatedTranslation)

    diff = getDiff(oldValues, newValues, allLanguages)
    applyDiff(key, diff, translations)

def editTranslationForKey(key, dictionary, translations):
    allLanguages = list(translations.keys())
    allLanguages.sort()

    changed, content = openEditor(key, dictionary, allLanguages)

    if changed:
        updateTranslation(key, content, dictionary, allLanguages, translations)

def main():
    argparser = argparse.ArgumentParser(
        prog='translations',
        description='Saves you from touching these messy translation files in just-hire-angular.'
    )
    argparser.add_argument(
        'KEY', nargs="?",
        help='The key that shall be edited or created. If no key is provided all available translations will be listed.')
    args = argparser.parse_args()

    translations = readTranslations(TRANSLATION_DIRECTORY)
    dictionary = buildTranslationsDictionary(translations)

    if args.KEY is not None:
        key = args.KEY
        editTranslationForKey(key, dictionary, translations)

    else:
        curses.wrapper(interactive)

def setupColors():
    curses.curs_set(0)
    curses.init_pair(COLOR_PAIR_TITLE, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_PAIR_KEY, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_PAIR_DESCRIPTION, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_PAIR_PATTERN, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
    curses.init_pair(COLOR_PAIR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)

    curses.init_pair(COLOR_PAIR_ADDED, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(COLOR_PAIR_DELETED, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(COLOR_PAIR_MODIFIED, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(COLOR_PAIR_MOVED, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(COLOR_PAIR_UNTRACKED, curses.COLOR_CYAN, curses.COLOR_BLACK)

    curses.init_pair(COLOR_PAIR_STAGED, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(COLOR_PAIR_CONFIRMATION, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(COLOR_PAIR_CONFIRMATION_SELECTION, curses.COLOR_BLACK, curses.COLOR_WHITE)

def addTitleBox(screen):
    title_background = BackgroundView(curses.color_pair(COLOR_PAIR_TITLE))
    screen.add_view(title_background, lambda w, h, v: (0, 0, w, 1))

    path = Path(TRANSLATION_DIRECTORY)
    try:
        relative = path.relative_to(Path.home())
        title = '~/' + str(relative)
    except ValueError:
        pass

    repoLabel = Label(title)
    repoLabel.attributes.append(curses.color_pair(COLOR_PAIR_TITLE))
    repoLabel.attributes.append(curses.A_BOLD)

    patternLabel = Label('['+TRANSLATION_PATTERN+']')
    patternLabel.attributes.append(curses.color_pair(COLOR_PAIR_PATTERN))
    patternLabel.attributes.append(curses.A_BOLD)

    titleHBox = HBox()
    titleHBox.add_view(repoLabel, Padding(0, 0, 0, 0))
    titleHBox.add_view(patternLabel, Padding(1, 0, 0, 0))
    screen.add_view(titleHBox,
                    lambda w, h, v: ((w - v.required_size().width) // 2, 0, titleHBox.required_size().width + 1, 1))

def addLegend(screen, legendItems):

    moreLabel = Label('')
    def setMoreLabel(clipped):
        moreLabel.text = '...' if clipped else ''

    legendHBox = HBox()
    legendHBox.clipping_callback = setMoreLabel

    for key, description in legendItems:
        keyLabel = Label(key)
        keyLabel.attributes.append(curses.color_pair(COLOR_PAIR_KEY))
        legendHBox.add_view(keyLabel, Padding(2, 0, 0, 0))

        descriptionLabel = Label(description)
        descriptionLabel.attributes.append(curses.color_pair(COLOR_PAIR_DESCRIPTION))
        legendHBox.add_view(descriptionLabel, Padding(0, 0, 0, 0))

    screen.add_view(legendHBox, lambda w, h, v: (0, h-1, w-moreLabel.required_size().width, 1))
    screen.add_view(moreLabel, lambda w, h, v: (w-v.required_size().width-1, h-1, v.required_size().width, 1))

    return [legendHBox, moreLabel]



def interactive(stdscr):

    setupColors()

    screen = ConstrainedBasedScreen(stdscr)
    addTitleBox(screen)
    legendElements = addLegend(screen, legends.MAIN)

    isFiltering = False

    while 1:
        screen.render()
        key = stdscr.getch()

        if isFiltering:
            if key == keys.ESCAPE:
                isFiltering = False
                screen.remove_views(legendElements)
                legendElements = addLegend(screen, legends.MAIN)

            if key == keys.ENTER:
                isFiltering = False
                screen.remove_views(legendElements)
                legendElements = addLegend(screen, legends.MAIN)

        else:
            if key == keys.F:
                isFiltering = True
                screen.remove_views(legendElements)
                legendElements = addLegend(screen, legends.FILTER)

            if key == keys.Q:
                exit(0)


if __name__ == '__main__':
    main()