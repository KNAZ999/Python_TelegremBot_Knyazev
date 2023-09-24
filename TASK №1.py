print('*' * 10, 'Игра крестики-нолики', '*' * 10)
# Напишите функцию draw_board(board), которая рисует доску размером 3х3. Функция принимает на вход двумерный список и выдает игровое поле.
board = list(range(1, 10))


def draw_board(board):
    # запустить цикл, который проходит по всем 3 строкам доски
    print('-' * 13)
    for i in range(3):
        # поставить разделители значений в строке
        print("|", board[0 + i * 3], "|", board[1 + i * 3], "|", board[2 + i * 3], "|")
        # поставить разделители строк
        print('-' * 13)


draw_board(board)


# Напишите функцию ask_and_make_move(player, board), которая позволяет пользователю делать ход.
def ask_and_make_move(player, board):
    # дать игроку возможность сделать ход, то-есть ввести координаты
    x, y = input(f"{player}, enter x and y coordinates (e.g. 0 0): ").strip().split()
    # преобразовать координаты в целые числа
    x, y = int(x), int(y)
    # задать условие, которое проверяет,
    # находится ли координата в пределах поля и свободно ли место
    if (0 <= x <= 2) and (0 <= y <= 2) and (board[x][y] == " "):
        # если свободно, записать значение игрока (Х или 0) в ячейку
        board[x][y] = player
    else:
        print("That spot is already taken. Try again.")


ask_and_make_move(player, board)
