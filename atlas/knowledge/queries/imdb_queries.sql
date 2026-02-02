-- Sample IMDB Queries
-- These are validated query patterns for common movie/TV analysis tasks

-- Query: highest_rated_movies
-- Description: Find highest-rated movies with credible vote counts
-- Tables: titles, ratings
SELECT
    t.primaryTitle,
    t.startYear,
    r.averageRating,
    r.numVotes
FROM titles t
INNER JOIN ratings r ON t.tconst = r.tconst
WHERE t.titleType = 'movie'
  AND r.numVotes > 100000
ORDER BY r.averageRating DESC
LIMIT 20;

-- Query: movies_by_genre_and_year
-- Description: Count movies by genre for a specific year
-- Tables: titles
SELECT
    startYear,
    genres,
    COUNT(*) as movie_count
FROM titles
WHERE titleType = 'movie'
  AND startYear BETWEEN 2010 AND 2020
  AND genres IS NOT NULL
GROUP BY startYear, genres
ORDER BY startYear DESC, movie_count DESC;

-- Query: actor_filmography
-- Description: Get all movies for a specific actor
-- Tables: titles, principals, people
SELECT
    t.primaryTitle,
    t.startYear,
    p.category,
    p.characters
FROM titles t
INNER JOIN principals p ON t.tconst = p.tconst
INNER JOIN people pe ON p.nconst = pe.nconst
WHERE pe.primaryName = 'Tom Hanks'
  AND p.category IN ('actor', 'actress')
  AND t.titleType = 'movie'
ORDER BY t.startYear DESC;

-- Query: director_average_ratings
-- Description: Find directors with highest average movie ratings
-- Tables: crew, titles, ratings, people
SELECT
    pe.primaryName as director_name,
    COUNT(*) as movie_count,
    ROUND(AVG(r.averageRating), 2) as avg_rating,
    SUM(r.numVotes) as total_votes
FROM crew c
INNER JOIN titles t ON c.tconst = t.tconst
INNER JOIN ratings r ON t.tconst = r.tconst
CROSS JOIN LATERAL unnest(string_to_array(c.directors, ',')) as director_id
INNER JOIN people pe ON pe.nconst = director_id
WHERE t.titleType = 'movie'
  AND r.numVotes > 10000
GROUP BY pe.primaryName
HAVING COUNT(*) >= 5
ORDER BY avg_rating DESC
LIMIT 20;

-- Query: movies_per_year_trend
-- Description: Analyze movie production trends over decades
-- Tables: titles
SELECT
    FLOOR(startYear / 10) * 10 as decade,
    COUNT(*) as movie_count,
    ROUND(AVG(runtimeMinutes), 0) as avg_runtime
FROM titles
WHERE titleType = 'movie'
  AND startYear >= 1920
  AND startYear <= 2020
  AND runtimeMinutes IS NOT NULL
GROUP BY decade
ORDER BY decade;

-- Query: genre_popularity
-- Description: Most common genres (handles comma-separated values)
-- Tables: titles
SELECT
    genre,
    COUNT(*) as count
FROM titles,
LATERAL unnest(string_to_array(genres, ',')) as genre
WHERE titleType = 'movie'
  AND startYear >= 2010
GROUP BY genre
ORDER BY count DESC
LIMIT 15;
