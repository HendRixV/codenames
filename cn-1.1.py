import pygame as pg
from pygame.locals import *
from pygame import QUIT, K_q, K_r, K_s, K_LCTRL, K_SPACE

import multiprocessing as mp
from multiprocessing import Manager

import os
from pathlib import Path
from random import sample, choices, shuffle, randint as ri

from math import sqrt


def get_files(path):
    return {root: [Path(root) / f for f in files] for root, dirs, files in os.walk(path) if files}


class Game:
    W, H = 1920, 1080

    def __init__(self):
        self.win = self.W, self.H  # win for window.
        self.fps = 30
        self.wflag = NOFRAME  # RESIZABLE
        self.font, self.bg = None, None
        self.gf, self.sf = None, None

        self.turn_len = 60
        self.t_font = None
        self.t_x, self.t_y = (self.W - self.W // 5), (self.H - self.H // 5)
        self.t_rect = pg.Rect(self.t_x, self.t_y, self.W - self.t_x, self.H - self.t_y)
        print(self.t_x, self.t_y, self.W - self.t_x, self.H - self.t_y)
        self.st_color, self.end_color = COLS['green'], (250, 79, 48)

        self.ban_w, self.ban_h = self.W * 0.73, self.H * 0.12
        self.ban_x, self.ban_y = (self.W * 0.78 - self.ban_w) // 2, (self.H - self.ban_h) // 2
        self.ban_rect = pg.Rect(self.ban_x, self.ban_y, self.ban_w, self.ban_h)
        self.win_ban, self.ban_font = None, None
        self.ban_lock = False

    def set_font(self):
        self.font = pg.font.SysFont('Ermilov', round(Card.C_H * 0.3))

    def set_timer_font(self):
        self.t_font = pg.font.SysFont('Ermilov', round((self.H - self.t_y) * 0.9))

    def set_bg(self):
        self.bg = pg.transform.scale(
            pg.image.load('./source/bg_night.jpg').convert(), self.win).subsurface((0, 0, self.W, self.H))

    def set_ban(self):
        ### Winner Banner ###
        self.ban_font = pg.font.SysFont('ubuntu', round(Game.H * 0.07))
        self.win_ban = pg.Surface((self.ban_w, self.ban_h))
        self.win_ban.set_alpha(200)
        self.win_ban.fill((0, 0, 0), None, pg.BLEND_RGBA_MULT)

    def set_clock(self):
        pass

    def win_set(self):
        self.set_font(), self.set_bg(), self.set_ban(), self.set_timer_font()

    def game_field(self, run, lock, active, rest, _words, _colors, _icons, g_news, timer):
        # Initialize Pygame
        pg.init()

        ### Sounds ###
        succ_snd = pg.mixer.Sound('./source/snd/success.ogg')
        vic_snd = pg.mixer.Sound('./source/snd/victory.ogg')
        wrong_snd = pg.mixer.Sound('./source/snd/wrong.ogg')
        death_snd = pg.mixer.Sound('./source/snd/death.ogg')
        start_snd = pg.mixer.Sound('./source/snd/start.ogg')
        stop_snd = pg.mixer.Sound('./source/snd/stop.ogg')
        pause_snd = pg.mixer.Sound('./source/snd/pause.ogg')
        resume_snd = pg.mixer.Sound('./source/snd/resume.ogg')
        restart_snd = pg.mixer.Sound('./source/snd/restart.ogg')
        switch_snd = pg.mixer.Sound('./source/snd/switch.ogg')
        # sndtrack_snd = pg.mixer.Sound('./source/snd/sndtrack.ogg')
        # sndtrack_snd.set_volume(0.2)
        death_snd.set_volume(0.7)

        # Set the dimensions of the first window
        self.gf = pg.display.set_mode(self.win, self.wflag)
        self.win_set()
        pg.display.set_caption('Кодові імена')

        teams = [team.set_icon() for team in Team.ALL_INST]

        _hide_img = set_hide()

        filler(Card.ALL_CARDS, _words, _colors, _icons, _hide_img)

        winner = {}
        clock, start_turn, pause, time_in_pause = pg.time.Clock(), None, True, 0

        while run.value:
            for ev in pg.event.get():
                if ev.type == QUIT:
                    with lock:
                        run.value = not run.value

            pressed_keys = pg.key.get_pressed()
            if pressed_keys[K_q] and pressed_keys[K_LCTRL]:
                stop_snd.play()
                pg.time.delay(600)
                with lock:
                    run.value = not run.value
            if pressed_keys[K_r]:
                restart_snd.play()
                reset_restart(rest, lock)  # Open the restart gate
                pg.time.delay(1000)
            if pressed_keys[K_SPACE]:
                if pause:
                    # Resume the timer, subtract the paused time from the time in pause.
                    resume_snd.play() if start_turn else start_snd.play()
                    start_turn = pg.time.get_ticks() - time_in_pause
                else:
                    # Pause the timer and store the elapsed time so far.
                    pause_snd.play()
                    time_in_pause = pg.time.get_ticks() - start_turn
                pause = not pause
                pg.time.delay(500)
            if pressed_keys[K_s]:
                # Skip turn.
                switch_snd.play()
                switch_turn(active)
                pg.time.delay(500)

            # Check for mouse click.
            if not pause:
                mouse_pressed = pg.mouse.get_pressed()
                if mouse_pressed[0] and not winner:  # Left mouse button
                    mouse_pos = pg.mouse.get_pos()
                    for card in Card.ALL_CARDS:
                        if card.rect.collidepoint(mouse_pos) and card.key:
                            card.key = None
                            _words[words.index(card.word)] = None
                            act_cards = get_active_cards()
                            act_team = get_team(active)
                            if card.color_name == 'red':
                                print(f'Команда {act_team.name} впіймала облизня')
                                death_snd.play()
                                winner_team_objs = get_winner_objs(act_cards, act_team)
                                winner = get_winner_info(winner, winner_team_objs, g_news, lock)
                                break
                            elif (card.color_name == 'gold' and
                                    len([c for t, c in act_cards.items() if t in Team.COLS]) == Team.T_NUM):
                                open_count = 0
                                shuffle(Card.ALL_CARDS)
                                for b_card in Card.ALL_CARDS:
                                    if open_count == 2:
                                        break
                                    elif b_card.color_name != act_team.color_name and b_card.key:
                                        b_card.key = None
                                        _words[words.index(b_card.word)] = None
                                        act_cards[b_card.color_name] -= 1
                                        open_count += 1
                                        print(f'Команда {act_team.name} відкрила "{b_card.color_name}" картку')

                            flow = [c for t, c in act_cards.items() if t in Team.COLS]
                            if len(flow) >= 2:  # 2 is minimal number of teams.
                                if card.color_name in (act_team.color_name, 'l_grey'):
                                    wrong_snd.play()
                                    switch_turn(active)
                                    start_turn = pg.time.get_ticks()  # reset the timer
                                    break
                                else:
                                    succ_snd.play()
                            else:
                                winner_team_objs = get_winner_objs(act_cards, act_team, True)
                                winner = get_winner_info(winner, winner_team_objs, g_news, lock)
                                vic_ch = vic_snd.play()
                                break

            if not not rest.value:
                filler(Card.ALL_CARDS, _words, _colors, _icons, _hide_img)
                winner, self.ban_lock = {}, False  # reset winner and ban_lock.
                start_turn, pause, timer.value = None, True, 60  # reset the timer.
                reset_restart(rest, lock)  # Close the restart gate.

            # Drawing and rendering for main window.
            self.gf.blit(self.bg, (0, 0))

            if not winner:
                # Draw cards
                for card in Card.ALL_CARDS:
                    image = card.hide_icon if card.key else card.true_icon
                    self.gf.blit(image, (card.x, card.y))
                    if card.key:
                        # Create a text surface
                        word_surf = self.font.render(card.word, True, COLS['white'])
                        word_rect = word_surf.get_rect(center=card.rect.center)

                        # Blit the text onto the square
                        self.gf.blit(word_surf, word_rect)

                for team, act in zip(teams, active):
                    self.gf.blit(team.icon, (team.x, team.y))
                    if not act:
                        self.gf.blit(Team.cover, (team.x, team.y))

                # Timer
                if not pause:
                    # Calculate the time for turn.
                    cur_time = pg.time.get_ticks()
                    elapsed_time = (cur_time - start_turn) // 1000  # Elapsed time in seconds.
                    timer.value = max(self.turn_len - elapsed_time, 0)  # Calculate remaining time

                if timer.value >= 1:
                    time_str, color = get_timer_info(timer.value, self)
                    timer_surf = self.t_font.render(time_str, True, color)
                    tim_rect = timer_surf.get_rect(center=self.t_rect.center)
                    self.gf.blit(timer_surf, tim_rect)
                else:
                    switch_snd.play()
                    switch_turn(active)  # If 60 seconds have passed, change turn
                    start_turn = pg.time.get_ticks()  # reset the timer

            else:
                for card in Card.ALL_CARDS:
                    self.gf.blit(card.true_icon, (card.x, card.y))

                self.gf.blit(self.win_ban, (self.ban_x, self.ban_y))
                # Create banner text surface
                if not self.ban_lock:
                    if isinstance(winner["name"], list):
                        gret_text = ''
                        for name in winner["name"]:
                            gret_text += f'«{name}»'
                        gret_text += 'перемогли!'
                        gret_text.replace('»«', '» та «')
                    else:
                        gret_text = f'«{winner["name"]}» перемогла!'
                    gret_surf = self.ban_font.render(gret_text, True, COLS['white'])
                    gret_rect = gret_surf.get_rect(center=self.ban_rect.center)
                    self.ban_lock = True

                # Blit the text onto the banner
                self.gf.blit(gret_surf, gret_rect)

                # Display winner team or teams
                if isinstance(winner['icon'], list):
                    for w_icon, w_ix, w_iy in zip(winner['icon'], winner['ix'], winner['iy']):
                        self.gf.blit(w_icon, (w_ix, w_iy))
                else:
                    self.gf.blit(winner['icon'], (winner['ix'], winner['iy']))

            pg.display.flip()
            clock.tick(self.fps)

        # Quit Pygame
        pg.quit()

    def speaker_field(self, run, lock, active, rest, _words, _colors, _icons, g_news, timer):
        # Initialize Pygame
        pg.init()

        # Set the dimensions of the second window
        self.sf = pg.display.set_mode(self.win, self.wflag)
        self.win_set()
        pg.display.set_caption('Зв\'язківцям')

        teams = [team.set_icon() for team in Team.ALL_INST]

        _hide_img = set_hide()

        filler(Card.ALL_CARDS, _words, _colors, _icons, _hide_img)

        winner = {}
        clock = pg.time.Clock()

        while run.value:
            for ev in pg.event.get():
                if ev.type == QUIT:
                    with lock:
                        run.value = not run.value

            pressed_keys = pg.key.get_pressed()
            if pressed_keys[K_q] and pressed_keys[K_LCTRL]:
                with lock:
                    run.value = not run.value

            if not not rest.value:
                reset_round(active, lock, _words, _colors, _icons, g_news, _hide_img)
                filler(Card.ALL_CARDS, _words, _colors, _icons, _hide_img)
                self.ban_lock = False
                pg.time.delay(1000)

            # Drawing and rendering for second window
            self.sf.blit(self.bg, (0, 0))

            for card in Card.ALL_CARDS:
                if card.key:
                    color = card.color_value if card.color_name not in ('red', 'gold') else COLS['l_grey']
                    pg.draw.rect(self.sf, color, card.rect)
                    try:
                        card.key = _words[_words.index(card.key)]
                    except Exception:
                        card.key = None

                    # Create a text surface
                    word_surf = self.font.render(card.word, True, COLS['white'])
                    word_rect = word_surf.get_rect(center=card.rect.center)

                    # Blit the text onto the square
                    self.sf.blit(word_surf, word_rect)
                else:
                    self.sf.blit(card.true_icon, (card.x, card.y))
            if not g_news.value:
                for team, act in zip(teams, active):
                    self.sf.blit(team.icon, (team.x, team.y))
                    if not act:
                        self.sf.blit(Team.cover, (team.x, team.y))

                time_str, color = get_timer_info(timer.value, self)
                timer_surf = self.t_font.render(time_str, True, color)
                tim_rect = timer_surf.get_rect(center=self.t_rect.center)
                self.sf.blit(timer_surf, tim_rect)

            else:
                if not self.ban_lock:
                    winner_team_objs = [t for t in teams if t.name in g_news.value][0]
                    winner = get_winner_info(winner, winner_team_objs, g_news, lock)
                    if isinstance(winner["name"], list):
                        gret_text = ''
                        for name in winner["name"]:
                            gret_text += f'«{name}»'
                        gret_text += 'перемогли!'
                    else:
                        gret_text = f'«{winner["name"]}» перемогла!'
                    gret_surf = self.ban_font.render(gret_text, True, COLS['white'])
                    gret_rect = gret_surf.get_rect(center=self.ban_rect.center)
                    self.ban_lock = True

                # Draw the win banner.
                self.sf.blit(self.win_ban, (self.ban_x, self.ban_y))
                # Blit the text onto the banner.
                self.sf.blit(gret_surf, gret_rect)
                # Display winner team icon.
                if isinstance(winner['icon'], list):
                    for w_icon, w_ix, w_iy in zip(winner['icon'], winner['ix'], winner['iy']):
                        self.sf.blit(w_icon, (w_ix, w_iy))
                else:
                    self.sf.blit(winner['icon'], (winner['ix'], winner['iy']))

            pg.display.flip()

            clock.tick(self.fps)
        # Quit Pygame
        pg.quit()


def fst_move(n):
    bool_list = [False] * n
    bool_list[ri(0, n - 1)] = True
    return bool_list


def switch_turn(turns):
    proxy = [*turns]
    act_ind = proxy.index(1)
    nex_ind = 0 if act_ind + 1 == Team.T_NUM else act_ind + 1
    for n_turn, turn in enumerate(turns):
        if n_turn in (act_ind, nex_ind):
            turns[n_turn] = not turn


def reset_turn(turns):
    for n_turn, new_turn in zip(range(len(turns)), fst_move(Team.T_NUM)):
        turns[n_turn] = new_turn


def reset_round(act, __lock, ___words, ___colors, ___icons, ___g_news, ___hide_img):
    reset_turn(act)
    set_good_news(___g_news, __lock, '')
    wiper(___words, ___colors, ___icons, __lock, act)


def reset_restart(restart_key, _lock):
    with _lock:
        restart_key.value = not restart_key.value
    # return restart_key


def set_good_news(__g_news, __lock, value):
    with __lock:
        __g_news.value = value


def get_timer_info(t_val, _game):
    _time_str = f'{t_val}'  # if t_val <= 9 else f'{t_val}'
    if t_val == ri(0, 5):  # or t_val == ri(60, 61):
        _color = COLS['red']
    # elif t_val <= 59:
    #     color_progress = 1.0 - (t_val / _game.turn_len)
    #     _color = (
    #         int(_game.st_color[0] + color_progress * (_game.end_color[0] - _game.st_color[0])),
    #         int(_game.st_color[1] + color_progress * (_game.end_color[1] - _game.st_color[1])),
    #         int(_game.st_color[2] + color_progress * (_game.end_color[2] - _game.st_color[2]))
    #     )
    else:
        _color = _game.st_color
    return _time_str, _color


def get_winner_objs(act_c, act_t, flag=False):
    if not flag:
        filtered_list = [(key, val) for key, val in list(act_c.items())
                         if key in Team.COLS and key != act_t.color_name]
    else:
        filtered_list = [(key, val) for key, val in list(act_c.items()) if key in Team.COLS]
    max_value = max(filtered_list, key=lambda x: x[1])[1]
    win_team_color = [pair[0] for pair in filtered_list if pair[1] == max_value]
    objs = [t for t in Team.ALL_INST if t.color_name in win_team_color]
    return objs


def get_winner_info(_winner, team_obj, _g_news, _lock):
    name = ''
    if isinstance(team_obj, list):
        if len(team_obj) > 1:
            names, _icons, ixs, iys = [], [], [], []
            for el in team_obj:
                name += el.name
                names.append(el.name), _icons.append(el.icon), ixs.append(el.x), iys.append(el.y)
            _winner.update({'name': names, 'icon': _icons, 'ix': ixs, 'iy': iys})
        else:
            team_obj = team_obj[0]
            _winner.update(
                {'name': team_obj.name, 'icon': team_obj.icon, 'ix': team_obj.x, 'iy': (Game.H - Team.T_D) // 2})
            name = team_obj.name
    else:
        _winner.update({'name': team_obj.name, 'icon': team_obj.icon, 'ix': team_obj.x, 'iy': (Game.H - Team.T_D) // 2})
        name = team_obj.name
    if not _g_news.value:
        set_good_news(_g_news, _lock, name)
    return _winner


class Team:
    T_NUM = 2
    T_SPACE = Game.H - Game.H // 5, Game.W // 5
    T_SP = 20  # space between icons
    T_H, T_W = (T_SPACE[0] - (T_NUM + 1) * T_SP) // T_NUM, T_SPACE[1] - 2 * T_SP
    T_D = min(T_H, T_W)  # team icon diameter
    T_NAMES = {'purple': 'Пантера', 'orange': 'Фенікс', 'blue': 'Яструб', 'pink': 'Валькірія'}
    # T_NAMES = {'purple': 'Пантера', 'orange': 'Фенікс', 'blue': 'Яструб', 'pink': 'Валькірія'}
    ALL_INST, COLS = [], []

    cover = pg.Surface((T_D, T_D), pg.SRCALPHA)
    pg.draw.circle(cover, (0, 0, 0, 215), (T_D//2 + 1, T_D//2 + 1), T_D//1.98)

    def __init__(self, color, ind):
        self.name, self.ind = self.T_NAMES[color], ind
        self.color_name, self.color_value = color, COLS[color]
        self.icon, self.x, self.y, self.rect = None, None, None, None
        Team.ALL_INST.append(self)
        Team.COLS.append(self.color_name)

    def set_icon(self):
        i_size, i_space = self.T_D, self.T_SP
        f_h, f_w = self.T_SPACE[0], Game.W - self.T_SPACE[1] + (self.T_SPACE[1] - i_size) // 2
        icon_path = f'./source/icons/{self.color_name}_icon.png'
        self.icon = pg.transform.scale(pg.image.load(icon_path).convert_alpha(), (i_size, i_size))
        self.x = f_w
        self.y = (f_h - (i_size * self.T_NUM + i_space * (self.T_NUM - 1)) + self.ind * (i_size + i_space))
        self.rect = pg.Rect(self.x, self.y, i_size, i_size)
        return self


def gen_teams():
    for num, t_color in zip(range(Team.T_NUM), Team.T_NAMES.keys()):
        Team(t_color, num)
    return Team.ALL_INST


def get_team(cur_pos, flag=None):
    for team, pos in zip(Team.ALL_INST, cur_pos):
        if not flag:
            if pos:
                return team
        else:
            if not pos:
                return team


class Card:
    ALL_CARDS = []
    CARDS4TEAMS = {2: 25, 3: 36, 4: 49}
    C_SPACE = Game.H, Game.W - Team.T_SPACE[1]
    C_QTY = CARDS4TEAMS[Team.T_NUM]
    C_ROW = round(sqrt(C_QTY))
    C_SP = 10
    C_W = round(((C_SPACE[1] - C_ROW * C_SP - 7 * C_SP) // C_ROW))
    C_H = round(C_W * (9 / 16))

    ICONS = get_files(f'./source/agents/')

    def __init__(self, poss):
        _row, _col, = poss
        c_w, c_h, c_sp, el_in_row = Card.C_W, Card.C_H, Card.C_SP, Card.C_ROW
        self.x = (Card.C_SPACE[1] - (c_w * el_in_row + c_sp * (el_in_row - 1))) // 2 + _col * (c_w + c_sp)
        self.y = (Card.C_SPACE[0] - (c_h * el_in_row + c_sp * (el_in_row - 1))) // 2 + _row * (c_h + c_sp)
        self.rect = pg.Rect(self.x, self.y, c_w, c_h)
        self.color_name, self.color_value = None, None
        self.hide_icon = None
        self.true_path, self.true_icon = None, None
        self.word, self.key = None, None
        Card.ALL_CARDS.append(self)

    def fill_card(self, color, word, icon_path, hide_img):
        self.color_name, self.color_value = color, COLS[color]
        self.hide_icon = hide_img.subsurface(pg.Rect(self.x, self.y, self.C_W, self.C_H))
        self.true_icon = pg.transform.scale(pg.image.load(icon_path).convert(), (self.C_W, self.C_H))
        self.word, self.key = word, word
        return self


def get_active_cards():
    count = {}
    for _c in Card.ALL_CARDS:
        if _c.key:
            cclor = _c.color_name
            if not count.get(cclor):
                count.update({cclor: 1})
            else:
                count[cclor] += 1
    return count


def wiper(__words, __colors, __icons, _lock, _act):
    Card.ICONS = get_files(f'./source/agents/')
    with _lock:
        new_colors = get_colors(_act)
        for i, n_w, n_c, n_i in zip(range(Card.C_QTY), get_words(), new_colors, icon_fits(new_colors)):
            __words[i], __colors[i], __icons[i] = n_w, n_c, n_i


def filler(cards, __words, __colors, __icons, __hide_img):
    for card, wor, colr, ico in zip(cards, __words, __colors, __icons):
        card.fill_card(colr, wor, ico, __hide_img)


def gen_cards():
    # Create a list of card objects
    for row in range(Card.C_ROW):
        for col in range(Card.C_ROW):
            Card((col, row))


def get_colors(act):
    teams_num, c_num, stab_c = Team.T_NUM, Card.C_QTY, 8
    cards_groups = (c_num - stab_c) // teams_num
    players_cols = Team.COLS
    painted_cards = []
    for el in range(stab_c):
        painted_cards.append('l_grey' if el != 0 else choices(('red', 'gold'), (0.7, 0.3))[0])
    for el, t_col in zip(range(teams_num), players_cols):
        for el_t in range(cards_groups):
            painted_cards.append(t_col)
    add_card = max(zip(players_cols, act), key=lambda x: x[1])[0]
    painted_cards.append(add_card)
    shuffle(painted_cards)
    return painted_cards


def get_words():
    with open('nouns.txt', 'r') as n_file:
        all_nouns = [line[:-1] for line in n_file.readlines()]
    return [noun[0].upper() + noun[1:] for noun in sample(all_nouns, k=Card.C_QTY)]


def set_hide():
    return pg.transform.scale(pg.image.load(f'./source/hide_1.jpg').convert(), (Game.W, Game.H))


def icon_fits(cur_colors):
    paths = []
    for each in cur_colors:
        icon = sample(Card.ICONS[f'./source/agents/{each}'], k=1)[0]
        paths.append(icon)
        Card.ICONS[f'./source/agents/{each}'].remove(icon)
    return paths


### Variables ###
COLS = {'white': (237, 221, 212),
        'grey': (23, 20, 18),
        'cover': (0, 0, 0, 164),
        'l_grey': (153, 153, 153),
        'black': (11, 10, 13),
        'red': (229, 16, 30),
        'blue': (0, 34, 225),  # 1F01B9
        'purple': (113, 0, 196),
        'orange': (230, 108, 24),
        'pink': (225, 1, 132),
        'gold': (225, 215, 0),
        'green': (1, 225, 119)}


if __name__ == "__main__":
    with Manager() as mn:
        # pregame setup
        locker = mp.Lock()
        gen_teams()
        act_teams = mp.Array('b', fst_move(Team.T_NUM))
        gen_cards()
        cards_colors = get_colors(act_teams)
        game = Game()

        # shared items
        words, colors, icons = mn.list(get_words()), mn.list(cards_colors), mn.list(icon_fits(cards_colors))
        good_news = mn.Value('str', '')
        running, restart = mp.Value('b', True), mp.Value('b', False)
        time_counter = mn.Value('int', 60)

        # Create two separate processes for each Pygame window
        gf_win = mp.Process(target=game.game_field, args=(running, locker, act_teams, restart,
                                                          words, colors, icons, good_news, time_counter))
        sf_win = mp.Process(target=game.speaker_field, args=(running, locker, act_teams, restart,
                                                             words, colors, icons, good_news, time_counter))

        # Start both processes
        gf_win.start()
        sf_win.start()

        # Wait for both processes to finish
        gf_win.join()
        sf_win.join()
