from gupy.geometry import Padding
from gupy.view import BackgroundView, Label, HBox, ListView
from gupy.screen import ConstrainedBasedScreen
from lib import colorpairs, keys, legends
from pathlib import Path
import curses


class UI:

    def __init__(self, translationDirectory, translationPattern):
        self.translationDirectory = translationDirectory
        self.translationPattern = translationPattern

    def setupColors(self):
        curses.curs_set(0)
        curses.init_pair(colorpairs.TITLE, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.KEY, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(colorpairs.DESCRIPTION, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.PATTERN, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(colorpairs.SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)

        curses.init_pair(colorpairs.ADDED, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.DELETED, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.MODIFIED, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.MOVED, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.UNTRACKED, curses.COLOR_CYAN, curses.COLOR_BLACK)

        curses.init_pair(colorpairs.STAGED, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(colorpairs.CONFIRMATION, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(colorpairs.CONFIRMATION_SELECTION, curses.COLOR_BLACK, curses.COLOR_WHITE)

    def addTitleBox(self, screen):
        title_background = BackgroundView(curses.color_pair(colorpairs.TITLE))
        screen.add_view(title_background, lambda w, h, v: (0, 0, w, 1))

        path = Path(self.translationDirectory)
        try:
            relative = path.relative_to(Path.home())
            title = '~/' + str(relative)
        except ValueError:
            pass

        repoLabel = Label(title)
        repoLabel.attributes.append(curses.color_pair(colorpairs.TITLE))
        repoLabel.attributes.append(curses.A_BOLD)

        patternLabel = Label('['+self.translationPattern+']')
        patternLabel.attributes.append(curses.color_pair(colorpairs.PATTERN))
        patternLabel.attributes.append(curses.A_BOLD)

        titleHBox = HBox()
        titleHBox.add_view(repoLabel, Padding(0, 0, 0, 0))
        titleHBox.add_view(patternLabel, Padding(1, 0, 0, 0))
        screen.add_view(titleHBox,
                        lambda w, h, v: ((w - v.required_size().width) // 2, 0, titleHBox.required_size().width + 1, 1))

    def addLegend(self, screen, legendItems):

        moreLabel = Label('')
        def setMoreLabel(clipped):
            moreLabel.text = '...' if clipped else ''

        legendHBox = HBox()
        legendHBox.clipping_callback = setMoreLabel

        for key, description in legendItems:
            keyLabel = Label(key)
            keyLabel.attributes.append(curses.color_pair(colorpairs.KEY))
            legendHBox.add_view(keyLabel, Padding(2, 0, 0, 0))

            descriptionLabel = Label(description)
            descriptionLabel.attributes.append(curses.color_pair(colorpairs.DESCRIPTION))
            legendHBox.add_view(descriptionLabel, Padding(0, 0, 0, 0))

        screen.add_view(legendHBox, lambda w, h, v: (0, h-1, w-moreLabel.required_size().width, 1))
        screen.add_view(moreLabel, lambda w, h, v: (w-v.required_size().width-1, h-1, v.required_size().width, 1))

        return [legendHBox, moreLabel]



    def loop(self, stdscr):

        self.setupColors()

        screen = ConstrainedBasedScreen(stdscr)
        self.addTitleBox(screen)
        legendElements = self.addLegend(screen, legends.MAIN)

        isFiltering = False

        while 1:
            screen.render()
            key = stdscr.getch()

            if isFiltering:
                if key == keys.ESCAPE:
                    isFiltering = False
                    screen.remove_views(legendElements)
                    legendElements = self.addLegend(screen, legends.MAIN)

                if key == keys.ENTER:
                    isFiltering = False
                    screen.remove_views(legendElements)
                    legendElements = self.addLegend(screen, legends.MAIN)

            else:
                if key == keys.F:
                    isFiltering = True
                    screen.remove_views(legendElements)
                    legendElements = self.addLegend(screen, legends.FILTER)

                if key == keys.Q:
                    exit(0)