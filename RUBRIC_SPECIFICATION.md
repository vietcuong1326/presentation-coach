# Rubric Specification --- MVP

Version: 1.0\
Status: Provisional mapping; official rubric wording must be confirmed.

## 1. Source rubric

The supplied rubric contains 20 criteria across Attitude, Project and
Presentation, each with five levels: - Superior = 5 - Excellent = 4 -
Very good = 3 - Satisfactory = 2 - Unacceptable = 1

The source rubric's criterion names and score scale are authoritative.
The MVP must not silently invent official level descriptors.

## 2. Required structured criterion fields

Each criterion should be represented as:

``` json
{
  "id": "LOGICALITY",
  "name": "Logicality",
  "category": "PROJECT",
  "scope": ["GROUP"],
  "required_inputs": ["SLIDE_TEXT", "TRANSCRIPT"],
  "level_descriptors": null,
  "mvp_supported": true,
  "limitations": []
}
```

`level_descriptors: null` means the official rubric does not provide
criterion-specific descriptions. A provisional descriptor may be drafted
for testing but must be labelled provisional and approved by the rubric
owner before formal scoring.

## 3. Initial criterion inventory

  ---------------------------------------------------------------------------
  Category          Criterion         Potential evidence    MVP status
  ----------------- ----------------- --------------------- -----------------
  Attitude          Preparation       Slide completeness,   Partial
                                      organization,         
                                      supplied preparation  
                                      evidence              

  Attitude          Cooperation       Transitions and       Limited
                                      attributable          
                                      interaction           

  Attitude          Punctuality       Submission/schedule   Not supported
                                      metadata              without metadata

  Attitude          Enthusiasm        Observable vocal      Limited
                                      delivery only; avoid  
                                      inner-state inference 

  Project           Content           Slide text +          Supported
                                      transcript +          
                                      objectives            

  Project           Logicality        Slide sequence +      Supported
                                      transcript            

  Project           Creativity        Novelty relative to   Limited
                                      topic/context         

  Project           Effectiveness     Evidence of objective Partial
                                      achievement/results   

  Project           Meaningfulness    Topic context and     Partial
                                      stated value          

  Project           References        References visible in Supported if
                                      slides/report         supplied

  Project           Scale             Project               Requires metadata
                                      scope/requirements    

  Presentation      Layout            Slide text and basic  Partial
                                      page structure        

  Presentation      Engaging the      Interaction evidence; Limited
                    audience          audience reaction may 
                                      be absent             

  Presentation      Speech volume &   Audio signal / speech Supported where
                    Speed             analysis              audio quality
                                                            permits

  Presentation      Language skills   Transcript            Supported

  Presentation      Pronunciation     Audio; transcript     Partial
                                      alone is insufficient 

  Presentation      Eye contact &     Video visual analysis Out of MVP
                    Posture                                 

  Presentation      Active            Attributable evidence Limited
                    participation     and task context      

  Presentation      MCQ test          Actual test and       Not supported
                                      results               without data

  Presentation      Report            Uploaded report       Supported only if
                                                            supplied
  ---------------------------------------------------------------------------

## 4. Group/individual mapping

This mapping is a product proposal, not an official interpretation: -
Group: shared project/presentation artifact criteria. - Individual:
speech delivery and language criteria where attribution is reliable. -
Mixed: preparation, cooperation, active participation and MCQ may need
both levels depending on evidence. - Punctuality is generally
project/submission-level unless the source rubric defines otherwise.

## 5. Not Evaluated policy

Use `NOT_EVALUATED` when: - Required source is absent. - Source is
unreadable or too poor quality. - Criterion is outside MVP scope. -
Evidence cannot be attributed reliably. - Rubric meaning is ambiguous
and no approved descriptor exists.

Never use score 0 as a substitute. Do not assign 1 merely because
evidence is missing.

## 6. Provisional descriptor workflow

For each criterion: 1. Ask rubric owner/teacher to define observable
behavior for levels 1--5. 2. Keep descriptors mutually distinguishable
and criterion-specific. 3. Add examples of evidence and borderline
cases. 4. Review against sample presentations. 5. Version the rubric. 6.
Store immutable rubric snapshot with each Evaluation.

## 7. Score aggregation

For evaluated criteria set E: - Earned points = sum of criterion
scores. - Available points = 5 × number of evaluated criteria. - Display
as `earned / available` and `evaluated_count / total_count`. - Do not
normalize partial results to 100. - Group and individual reports must
make scope clear. Do not add group and individual scores together if
that double-counts shared criteria.
