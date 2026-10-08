# amt = int(float(input('How much money do you have? \n'))*100)
# q = amt//25
# r = amt % 25
# d = r // 10
# s = r % 10
# n = r // 5
# p = n % 5
# print(amt)
# print(q, d, n, p)
pennies =round(float(input('How much money do you have?\n'))*100)
# print(pennies)
Quarters = pennies // 25
# print(Quarters)
CAQ = pennies % 25
# print(CAQ)
Dimes = CAQ // 10
# print(Dimes)
CAD = CAQ % 10
# print(CAD)
Nickels = CAD // 5
end_pennies = CAD % 5

print(f'Wow you could convert that to {Quarters} Quarters and have {Dimes} dime(s) {Nickels} nickel(s) and {end_pennies} cent(s) leftover. Let\'s hit the ARCADE!!')

