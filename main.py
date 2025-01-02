from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.userauth.router import userRouter
from backend.externalservice.router import BoardRouter
from backend.Graph.router import GraphRouter
from backend.Settings.router import serverRouter
from backend.report.router import ReportRouter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.0.84:9000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(userRouter)
app.include_router(serverRouter)
app.include_router(BoardRouter)
app.include_router(GraphRouter)
app.include_router(ReportRouter)