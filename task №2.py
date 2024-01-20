print('*' * 10, 'Игра крестики-нолики', '*' * 10)

board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]

player = "X"

from colorama import init, Fore
from colorama import Back
init(autoreset=True)
def draw_board(board):
    # запустить цикл, который проходит по всем 3 строкам доски
    for i in range(3):
        # поставить разделители значений в строке
        print(" | ".join(board[i]))
        # поставить разделители строк
        print("---------")


def ask_and_make_move(player, board):
    x, y = ask_move(player, board)
    # координаты x, y взять из функции ask_move(player, board)
    make_move(player, board, x, y)

def ask_move(player, board):
    # дать игроку возможность сделать ход, то есто есть ввести координаты
    x, y = input(f"{player}, enter x and y coordinates (e.g. 0 0): ").strip().split()
    # преобразовать координаты в целые числа
    x, y = int(x), int(y)
    # задать условие, которое проверяет, свободно ли место
    if (0 <= x <= 2) and (0 <= y <= 2) and (board[x][y] == Back.YELLOW + ' '):
        # если клетка свободна, вернуть её координаты
        return (x, y)
    else:
        print("Клетка занята. Введите координаты еще раз.")
        return ask_move(player, board)

def make_move(player, board, x, y):
    # проверить, что клетка свободна
    if board[x][y] != Back.YELLOW + ' ':
        print("Клетка занята")
        return False
    # если клетка свободна, записать ход
    board[x][y] = player
    return True

def check_win(player, board):
    # проверить, совпадают ли значения в строках и столбцах
    for i in range(3):
        # проверить, совпадают ли значения в строках
        if board[i] == [player, player, player]:
            return True
        # проверить, совпадают ли значения в столбцах
        if board[0][i] == player and board[1][i] == player and board[2][i] == player:
            return True
    # проверить, совпадают ли значения на диагонали из верхнего левого в нижний правый угол
    if board[0][0] == player and board[1][1] == player and board[2][2] == player:
        return True
    # проверить, совпадают ли значения на диагонали из верхнего правого в нижний левый угол
    if board[0][2] == player and board[1][1] == player and board[2][0] == player:
        return True
    return False

def tic_tac_toe():
    # задать бесконечный цикл, который проводит игры
    while True:
        board = [[Back.YELLOW + ' ' for i in range(3)] for j in range(3)]
        player = (Fore.RED + 'X')
        # задать бесконечный цикл, который проводит конкретную игру
        while True:
            # нарисовать игровое поле
            draw_board(board)
            # запросить ход
            ask_and_make_move(player, board)
            # проверить, выиграл ли игрок
            if check_win(player, board):
                print(f"{player} выиграли!")
                break
            # проверить, произошла ли ничья
            tie_game = False
            for row in board:
                for cell in row:
                    if cell == Back.YELLOW + ' ':
                        tie_game = True
            # если произошла ничья, завершить цикл
            if not tie_game:
                break
            player = (Fore.BLUE + 'O') if player == (Fore.RED + 'X') else (Fore.RED + 'X')

        # спросить игроков, хотят ли они сыграть еще нраз
        restart = input("Хотите сыграть еще раз? (y/n) ")
        if restart.lower() != "y":
            break

tic_tac_toe()
