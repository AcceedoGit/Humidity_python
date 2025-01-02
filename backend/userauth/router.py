from fastapi import APIRouter, HTTPException, Query,Request,Depends
from passlib.context import CryptContext
from configuration.database import users
from backend.userauth.schemas import User
from fastapi.security import OAuth2PasswordBearer
import hashlib
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

userRouter = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

active_tokens = set()

def verify_sha256(password: str, hashed_password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed_password

@userRouter.get("/api/v1/login")
async def login_user(username: str = Query(...), password: str = Query(...)):
    existing_user = users.find_one({"username": username})
    
    if existing_user is None:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    stored_password = existing_user["password"]

    # Password verification logic
    if stored_password.startswith("$"):  # Assuming a hashed password format
        if not pwd_context.verify(password, stored_password):
            raise HTTPException(status_code=400, detail="Invalid password!")
    elif len(stored_password) == 64:  # Assuming SHA-256 hashed password
        if not verify_sha256(password, stored_password):
            raise HTTPException(status_code=400, detail="Invalid password!")
    else:
        raise HTTPException(status_code=400, detail="Unsupported password format")
    
    # Generate a new token (this is a placeholder; implement actual token generation logic)
    token = "your_generated_token"  # Replace with actual token generation
    active_tokens.add(token)  # Add the token to the active tokens set

    return {"status": "success", "access_token": token, "token_type": "bearer"}

#USER PAGE
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@userRouter.get("/api/v1/users")
async def get_all_users():
    user_list = list(users.find())  

    if not user_list:
        raise HTTPException(status_code=404, detail="No users found")

    for user in user_list:
        user.pop("_id") 
    
    return {"users": user_list}

@userRouter.post("/api/v1/users/create")
async def create_user(user: User, request: Request):
    existing_user = users.find_one({"user_ID": user.user_ID})

    if existing_user:
        raise HTTPException(status_code=400, detail="User ID already exists")
    try:
        hashed_password = hash_password(user.password)
        new_user = {
            "user_ID": user.user_ID,
            "username": user.username,
            "role": user.role,
            "emailId": user.emailId,
            "phoneNo": user.phoneNo,
            "password": hashed_password,
        }  
        users.insert_one(new_user)
        
        return {"msg": "User registered successfully"}
    except Exception as e:
        print("Error creating user:", str(e))  # Log the error for debugging
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Update an 
@userRouter.put("/api/v1/users/update/{user_ID}")
async def update_user(user_ID: str, user: User):
    logging.info(f"Received a PUT request for /update/{user_ID}")
    
    existing_user = users.find_one({"user_ID": user_ID})
    
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_password = hash_password(user.password)
    
    updated_user = {
        "username": user.username,
        "role": user.role,
        "emailId": user.emailId,
        "phoneNo": user.phoneNo,
        "password": hashed_password,
    }
    
    users.update_one({"user_ID": user_ID}, {"$set": updated_user})    
    return {"msg": "User updated successfully"}

@userRouter.delete("/api/v1/users/delete/{user_ID}")
async def delete_user(user_ID: str):
    logging.info(f"Received a DELETE request for /delete/{user_ID}")
    
    existing_user = users.find_one({"user_ID": user_ID})
    
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    users.delete_one({"user_ID": user_ID})
    
    logging.info(f"User with ID {user_ID} has been deleted.")
    return {"msg": "User deleted successfully"}



@userRouter.post("/api/v1/logout")
async def logout_user(token: str = Depends(oauth2_scheme)):
    # Check if the token is valid
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Invalidate the token
    active_tokens.remove(token)

    return {"status": "success", "message": "Logged out successfully"}