from pathlib import Path
from typing import Dict, Any, List
import json, csv
import os

# Base directory where all movie folders are stored, ie data file
baseDir = Path(__file__).resolve().parents[1] / "data"

#returns path to movie folder
def getMovieDir(movieName: str) -> Path:
    return baseDir / movieName

#builds the full path to data/<movieName>/metadata.json
def loadMetadata(movieName: str) -> Dict[str, Any]:
    path = getMovieDir(movieName) / "metadata.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
#builds full path to access revies of movies
def loadReviews(movieName: str) -> List[Dict[str, str]]:
    path = getMovieDir(movieName) / "movieReviews.csv"
    if not path.exists():
        return []
    
    # Mapping from CSV column names to schema field names
    columnMapping = {
        "Date of Review": "dateOfReview",
        "User": "user",
        "Usefulness Vote": "usefulnessVote",
        "Total Votes": "totalVotes",
        "User's Rating out of 10": "userRatingOutOf10",
        "Review Title": "reviewTitle",
        "Review": "review"
    }
    
    reviews = []
    try:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for rowNum, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                try:
                    # Convert CSV column names to schema field names
                    mappedRow = {}
                    for csvCol, schemaCol in columnMapping.items():
                        if csvCol in row:
                            value = row[csvCol]
                            
                            # Clean and validate specific fields
                            if schemaCol == "userRatingOutOf10":
                                # Remove whitespace and validate it's a number
                                value = value.strip()
                                if not value or value == "":
                                    print(f"Skipping row {rowNum} in {movieName}: empty rating")
                                    continue
                                try:
                                    float(value)  # Validate it's parseable
                                except ValueError:
                                    print(f"Skipping row {rowNum} in {movieName}: invalid rating '{value}'")
                                    continue
                            
                            elif schemaCol == "review":
                                # Truncate reviews that are too long (max 5000 chars)
                                if len(value) > 5000:
                                    value = value[:4997] + "..."
                                    print(f"Truncated review in row {rowNum} of {movieName}")
                            
                            elif schemaCol == "reviewTitle":
                                # Truncate review titles that are too long (max 200 chars)
                                if len(value) > 200:
                                    value = value[:197] + "..."
                            
                            mappedRow[schemaCol] = value
                    
                    # Only add if we have all required fields
                    if len(mappedRow) == len(columnMapping):
                        reviews.append(mappedRow)
                    
                except Exception as e:
                    print(f"Error processing row {rowNum} in {movieName}: {e}")
                    continue
                    
    except Exception as e:
        print(f"Error loading reviews for {movieName}: {e}")
        return []
    
    return reviews

#saves movie to files, checks to see if there is a file with the movies name, if not it creates one as well
def saveMetadata(movieName: str, metadata: Dict[str, Any]) -> None:
    path = getMovieDir(movieName) / "metadata.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def saveReviews(movieName: str, reviews: List[Dict[str, str]]) -> None:
    path = getMovieDir(movieName) / "movieReviews.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    
    # CSV column order must match existing files
    csvFieldnames = [
        "Date of Review",
        "User",
        "Usefulness Vote",
        "Total Votes",
        "User's Rating out of 10",
        "Review Title",
        "Review"
    ]
    
    # Mapping from schema field names to CSV column names
    reverseMapping = {
        "dateOfReview": "Date of Review",
        "user": "User",
        "usefulnessVote": "Usefulness Vote",
        "totalVotes": "Total Votes",
        "userRatingOutOf10": "User's Rating out of 10",
        "reviewTitle": "Review Title",
        "review": "Review"
    }
    
    if reviews:
        # Convert schema field names back to CSV column names
        csvReviews = []
        for review in reviews:
            csvRow = {}
            for schemaCol, csvCol in reverseMapping.items():
                if schemaCol in review:
                    csvRow[csvCol] = review[schemaCol]
            csvReviews.append(csvRow)
        
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csvFieldnames)
            writer.writeheader()
            writer.writerows(csvReviews)
        os.replace(tmp, path)
    elif path.exists():
        path.unlink()



