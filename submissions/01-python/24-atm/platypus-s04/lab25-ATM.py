# default balance 0, interest rate 0.001%


class ATM:
    def __init__(self, balance=0, interest=0.001):
        self.balance = balance
        self.interest = interest
        self.transactions = []

    def check_balance(self):  # returns account balance
        return f'Your balance is currently at ${self.balance}'

    def print_transactions(self):  # maintains a list of transactions
        print('\n'.join(self.transactions))


    def deposit(self, amount):  # deposits the given amount into account
        self.balance += amount
        self.transactions.append(f'user deposited ${amount}')
        return f'you have deposited ${amount} into your account'

    def check_withdrawal(self, amount):  # returns true if the withdrawn amount wont put the account in the negative
        return amount < self.balance

    def withdraw(self, amount):  # withdraws the amount from the account and returns it
        self.balance -= amount
        self.transactions.append(f'user withdrew ${amount}')
        return f'your withdrawal amount is ${amount}'

    def calc_interest(self, interest):  # returns the amount of interest
        self.balance += self.balance * interest
        return f'you have gained {interest} on your account'




# atm = ATM()
# print(atm.check_balance())  # "your balance is $0"
# atm.deposit(55)
# print(atm.check_balance())  # "your balance is $5"
# print(atm.check_withdrawal(0))  # False
# print(atm.withdraw(10))  # 2
# print(atm.check_balance())  # "your balance is $3"
# print(atm.calc_interest(.001))
# print(atm.check_balance())  # "your balance is $3"
# print(atm.transactions)

atm = ATM()

while True:
    user = input('what would you like to do (deposit, withdraw, check balance, history, exit)? ').lower()
    if user in ['done', 'exit', 'quit']:
        print('goodbye!')
        break
    elif user == 'deposit':
        amount = float(input('how much would you like to deposit? '))
        atm.deposit(amount)

    elif user == 'withdraw':
        amount = float(input('how much would you like to withdraw? '))
        if atm.check_withdrawal(amount):
            atm.withdraw(amount)
        else:
            print('You do not have enough to withdrawal.')

    elif user == 'check balance':
        atm.check_balance()
        print(f'Your account balance is ${atm.check_balance()}')

    elif user == 'history':
        atm.print_transactions()





# $5
# what would you like to do (deposit, withdraw, check balance, history)?
# check balance
# balance: $5