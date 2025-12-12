# Interview Analytics Approach

## Objective
Optimizing the onsite pass through rate:  Support headgrowth aligned with optimized use of hiring resources

## Context
The onsite interview is an important part of the culture and provides a reliable signal for the best talent. The in-office project nature of the interview is also resource intensive, and, as implelented, somewhat subjective.  There is some anecdotal evidence that the onsite is allowing Cursor to pass on great candidates, and may, as hiring increases, cause some confusion on what type of candidates

Here we are going to propose a stuctured approach to evaluating our onsite interview.

If we're successful in this anlaysis we would expect to see increase in the number of candidates that pass from onsite to offer.

## Key Questions We're Answering
We're proposing 5 quesitons to answer to help form a somewhat robust anwer to the question "What can we do to optimize onsites (mostluy for Engineering, but hopefully applicable to other parts of Cursor)

1. **Do we have an onsite problem**: The onsite is a super important part of the culture.  It seems to me to be a key part of ensuring a good candidate experience.  The goal here is to have a pass through rate that’s balances high hiring bar with actually hiring people - 1 in 4 is a benchmark that's pretty common.  

2. **Pre-Screening Gaps**: Are there characteristics of candidates who don’t pass Onsite we could screen for at previous stages that would help prevent bad candidates from moving to Onsite?  What other patterns in onsite rejections could we detect earlier?

3. **Do we have false negatives**: Are we rejecting good candidates?  We might know this because there are dissenting views, or  close calls due to single dissenting votes.

4. **Are interviewers calibrated**: Here we are looking for people that always say yes or no, or people who are not often calibrated with the rest of the interview panel.  For later, we could also evaluate quality of feedback and have some mechanism for interviewers to rate each other on the quality of their feedback 

5. **Do we have false positives**: Are our interview signals predictive of success?  Are there peple who left Cursor for some reason we should have detected in the interview?

## Methodology
- Data sourced from Ashby ATS via API
- Stage progression tracked through application history
- Feedback analyzed for patterns using OpenAI
- All metrics filterable by department

## Caveats
- This was built without much familiarity with the underlyinig processes and design of Ashby and Cursor's recruiting processess - I  may have interpreted some data incorrectly.
- I did not do a proper assessment of data quality - 
Start with the **Funnel Ratios** tab to understand overall flow

## For the future
1. Qualitative research:  There are some cases (ML engineers from Windsurf) that would benefit from some interviews and qualitative research to understand what we're missing for signals. 
2. Use **Pre-Onsite Screening** to identify what to screen earlier
3. Review **False Negatives** to find potentially good candidates we rejected
4. Check **Interviewer Calibration** for training opportunities

