from fastapi import FastAPI, HTTPException, Depends, Query
import requests
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

client = MongoClient("mongodb://localhost:27017")
db = client.web
collection = db.book  # Коллекция товаров

app = FastAPI() 

class Book(BaseModel):
    google_book_id: str = Field(min_length=1)
    title: str
    authors: List[str] =  Field(..., min_items=1)
    published_date: Optional[str] = None
    description: str

def analyze_book(book):
    volume_info = book.get("volumeInfo", {})
    google_book = Book(
        google_book_id = book.get('id'),
        title = volume_info.get('title', 'Unknown'),
        authors = volume_info.get('authors', ['Unknown']),
        published_date = volume_info.get('publishedDate','Unknown'),
        description = volume_info.get('description','Unknown')
    )
    return google_book

#create
@app.post("/books/create", response_model=dict)
def create_books(book: Book):
    new_book = book.dict()
    result = collection.insert_one(new_book)
    if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to insert book")
    return {"id": str(result.inserted_id)}

#read
@app.get("/books/get", response_model=List[dict])
def get_books():
    books = list(collection.find())
    for book in books:
        book["id"] = str(book["_id"])
        del book["_id"]
    return books

#read books from google books api
@app.get("/books/googleapi")
async def get_google_books(query: str = Query(..., description="Book title")):
    API_KEY="AIzaSyBGh65pb-jiy5sUqrj9l3cUpbU-hWX_rVo"
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Google Books API error: {response.status_code}")
        raise HTTPException(status_code=500, detail="Error with Google Books API")
    result = response.json()
    books = result.get("items", [])
    google_books=[]
    for book in books:
        google_books.append(analyze_book(book))
    return google_books

#read free books from google books api
@app.get("/books/googleapi/freebooks")
async def get_free_google_books(query: str = Query(..., description="Book title")):
    API_KEY="AIzaSyBGh65pb-jiy5sUqrj9l3cUpbU-hWX_rVo"
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&filter=free-ebooks&key={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Google Books API error: {response.status_code}")
        raise HTTPException(status_code=500, detail="Error with Google Books API")
    result = response.json()
    books = result.get("items", [])
    google_books=[]
    for book in books:
        google_books.append(analyze_book(book))
    return google_books

# add book from google books 
@app.post("/books/add_google_book", response_model=dict)
async def add_google_book(book_id: str = Query(..., description="Book id from Google API")):
    url = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching book from Google API")
    result = response.json()
    new_book = analyze_book(result)
    result = collection.insert_one(new_book.dict())
    return {"id": str(result.inserted_id)}

#update
@app.put("/books/update/{book_id}", response_model=dict)
def update_book(book_id: str, book: Book):
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Invalid book ID format")
    result = collection.update_one({"_id": ObjectId(book_id)}, {"$set": book.dict()})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book updated successfully"}

#delete
@app.delete("/books/delete/{book_id}", response_model=dict)
def delete_book(book_id: str):
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Invalid book ID format")
    result = collection.delete_one({"_id": ObjectId(book_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted successfully"}

#delete all books
@app.delete("/books/deleteall", response_model=dict)
def delete_all_books():
    result = collection.delete_many({})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No books in database")
    return {"message": "Books deleted successfully"}


