# API Documentation

This document describes the APIs provided by the Explainable Eligibility Engine, implemented in the `api/` folder.

## Overview

The API is built using FastAPI and provides endpoints for evaluating welfare scheme eligibility, performing what-if analyses, gap analyses, and generating counterfactual scenarios. It integrates with the rule engine, scheme loader, and LLM components.

## Endpoints

### 1. `/evaluate` (POST)
Evaluates a user's profile against a specific welfare scheme.

**Request Body:**
```json
{
  "scheme_id": "string",
  "profile": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**Response:**
```json
{
  "scheme_id": "string",
  "scheme_name": "string",
  "eligible": boolean,
  "status": "string",
  "failed_reasons": ["string"],
  "trace": [{}],
  "structured_explanation": "string",
  "llm_explanation": "string"
}
```

### 2. `/evaluate_all` (POST)
Evaluates a user's profile against all available schemes.

**Request Body:**
```json
{
  "profile": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**Response:**
```json
{
  "matches": [
    {
      "scheme_id": "string",
      "scheme_name": "string",
      "eligible": boolean,
      "status": "string",
      "pass_ratio": number,
      "failed_reasons": ["string"],
      "trace": [{}],
      "structured_explanation": "string",
      "llm_explanation": "string"
    }
  ],
  "groups": {
    "eligible": [{}],
    "partially_eligible": [{}],
    "not_eligible": [{}]
  }
}
```

### 3. `/baseline` (POST)
Runs a baseline evaluation using the LLM for a specific scheme.

**Request Body:**
```json
{
  "scheme_id": "string",
  "profile": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**Response:**
```json
{
  "scheme_name": "string",
  "baseline_output": "string"
}
```

### 4. `/what-if` (POST)
Performs what-if analysis by evaluating a modified profile against all schemes.

**Request Body:**
```json
{
  "profile": {
    "field1": "value1",
    "field2": "value2"
  },
  "modifications": {
    "field": "new_value"
  }
}
```

**Response:**
```json
{
  "modifications": {},
  "scenarios": [
    {
      "scheme_id": "string",
      "scheme_name": "string",
      "before": {
        "eligible": boolean,
        "status": "string",
        "pass_ratio": number
      },
      "after": {
        "eligible": boolean,
        "status": "string",
        "pass_ratio": number
      },
      "changed": boolean,
      "improvements": ["string"]
    }
  ],
  "summary": "string"
}
```

### 5. `/gap-analysis` (POST)
Analyzes failed conditions for a scheme and ranks them by closeness to passing.

**Request Body:**
```json
{
  "scheme_id": "string",
  "profile": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**Response:**
```json
{
  "scheme_id": "string",
  "scheme_name": "string",
  "status": "string",
  "failed_count": number,
  "gaps": [
    {
      "field": "string",
      "description": "string",
      "actual": any,
      "required": any,
      "operator": "string",
      "distance": number,
      "suggestion": "string"
    }
  ],
  "summary": "string"
}
```

### 6. `/counterfactuals` (POST)
Generates counterfactual scenarios showing minimal changes to become eligible for a scheme.

**Request Body:**
```json
{
  "scheme_id": "string",
  "profile": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**Response:**
```json
{
  "scheme_id": "string",
  "scheme_name": "string",
  "is_eligible": boolean,
  "scenarios": [
    {
      "field": "string",
      "current_value": any,
      "required_value": any,
      "suggested_value": any,
      "feasibility_score": number,
      "feasibility_label": "string",
      "rationale": "string"
    }
  ],
  "summary": "string",
  "multiple_paths": boolean,
  "feasible_paths": [{}]
}
```

### 7. `/counterfactuals-all` (POST)
Generates counterfactual scenarios for all schemes.

**Request Body:**
```json
{
  "profile": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

**Response:**
```json
{
  "profile": {},
  "summary": {
    "eligible": number,
    "have_feasible_improvements": number,
    "no_feasible_improvements": number
  },
  "results": {
    "eligible": [{}],
    "have_feasible_improvements": [{}],
    "no_feasible_improvements": [{}]
  }
}
```

### 8. `/` (GET)
Health check endpoint.

**Response:**
```json
{
  "message": "API running"
}
```

## Features Module

The `features.py` file contains the implementation logic for advanced features:

- **What-If Analysis**: Evaluates how changes to a profile affect eligibility across schemes.
- **Gap Analysis**: Identifies and ranks failed conditions by how close they are to passing.
- **Counterfactual Scenarios**: Generates actionable suggestions for becoming eligible, ranked by feasibility.

Key functions:
- `evaluate_what_if()`: Performs what-if analysis.
- `evaluate_gap_analysis()`: Analyzes gaps for a scheme.
- `evaluate_counterfactuals()`: Generates counterfactuals for a scheme.
- `evaluate_all_counterfactuals()`: Generates counterfactuals for all schemes.

## Dependencies

- FastAPI
- Pydantic
- Existing modules: scheme_loader, rule_engine, llm components, baseline</content>
<parameter name="filePath">/Users/sid/Workstation/Code-Projects/welfare-ai/api/api_documentation.md