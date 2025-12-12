SELECT 
    interviewer_name,
    COUNT(*) as interviews,
    AVG(overall_rating) as avg_rating,
    SUM(CASE WHEN vote LIKE '%Hire%' AND vote NOT LIKE '%No%' THEN 1 ELSE 0 END) as hire_votes
FROM feedback
GROUP BY interviewer_name
ORDER BY interviews DESC;


select distinct vote 

from feedback