from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()  

def createhash(password:str)-> str:  
    return password_hash.hash(password)
    
def verifyhash(plainpassword:str, hashedpassword:str)-> bool:
    return password_hash.verify(plainpassword,hashedpassword)

