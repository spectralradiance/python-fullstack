import string
import random

password_in = input("Need a password? ")
#length = int(input("How long does it need to be? "))
lower_1 = int(input("How many lowercase letters? "))
upper_1 = int(input("How many uppercase letters? "))
digit_1 = int(input("How many numbers do you need? "))
punc_1 = int(input("How many special characters?"))

for i in range(lower_1):
    i += 1
    lower_2 = random.choice(string.ascii_lowercase)
    for i in range(upper_1):
        i += 1
        upper_2 = random.choice(string.ascii_uppercase)
        for i in range(digit_1):
            i  += 1
            digit_2 = random.choice(string.digits)
    for i in range(punc_1):
        i += 1
    punc_2 = random.choice(string.punctuation)
    random_password = lower_2 + upper_2 + digit_2 + punc_2
    random_password = list(random_password)
    random.shuffle(random_password)
    random_password = ''.join(random_password)
    print(random_password, end='')

# for i in range(length):
#     random_password = (random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation))
    # random_password = list(random_password)
    # random.shuffle(random_password)
    # random_password = ''.join(random_password)
    #print(random_password, end='')



