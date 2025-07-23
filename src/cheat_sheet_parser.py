"""Parser for DataPrime cheat sheet to extract structured knowledge."""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class DataPrimeOperator:
    """Structured information about a DataPrime operator."""
    name: str
    aliases: List[str]
    description: str
    syntax: str
    examples: List[str]
    category: str
    parameters: List[Dict[str, str]]

@dataclass
class DataPrimeFunction:
    """Structured information about a DataPrime function."""
    name: str
    signature: str
    description: str
    examples: List[str]
    category: str
    return_type: str
    parameters: List[Dict[str, str]]

class DataPrimeCheatSheetParser:
    """Parser for DataPrime cheat sheet markdown file."""
    
    def __init__(self, cheat_sheet_path: str = "data/dataprime_cheat_sheet.md"):
        self.cheat_sheet_path = Path(cheat_sheet_path)
        self.operators: List[DataPrimeOperator] = []
        self.functions: List[DataPrimeFunction] = []
        self.concepts: Dict[str, str] = {}
        self.examples_by_category: Dict[str, List[str]] = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse the cheat sheet and return structured knowledge."""
        with open(self.cheat_sheet_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse different sections
        self._parse_concepts(content)
        self._parse_operators(content)
        self._parse_functions(content)
        self._parse_examples(content)
        
        return {
            "operators": [op.__dict__ for op in self.operators],
            "functions": [fn.__dict__ for fn in self.functions],
            "concepts": self.concepts,
            "examples_by_category": self.examples_by_category,
            "summary": {
                "total_operators": len(self.operators),
                "total_functions": len(self.functions),
                "operator_categories": list(set(op.category for op in self.operators)),
                "function_categories": list(set(fn.category for fn in self.functions))
            }
        }
    
    def _parse_concepts(self, content: str) -> None:
        """Extract key DataPrime concepts."""
        concepts = {
            "query_format": self._extract_section(content, "Query Format"),
            "data_types": self._extract_section(content, "Data Types"),
            "field_access": self._extract_section(content, "Field Access"),
            "expressions": self._extract_section(content, "Expressions")
        }
        
        for concept, text in concepts.items():
            if text:
                self.concepts[concept] = text[:500]  # Truncate for brevity
    
    def _parse_operators(self, content: str) -> None:
        """Parse DataPrime operators from the cheat sheet."""
        
        # Define operator patterns and their locations in the text
        operator_patterns = [
            # Core operators
            ("source", ["source"], "Set the data source", "Data Source"),
            ("filter", ["filter", "f", "where"], "Filter events based on conditions", "Filtering"),
            ("groupby", ["groupby"], "Group results and calculate aggregations", "Aggregation"),
            ("aggregate", ["aggregate"], "Calculate aggregations over input", "Aggregation"),
            ("orderby", ["orderby", "sortby", "order by", "sort by"], "Sort data", "Sorting"),
            ("limit", ["limit"], "Limit output to specified number of events", "Limiting"),
            ("top", ["top"], "Get top N results", "Sorting"),
            ("bottom", ["bottom"], "Get bottom N results", "Sorting"),
            ("choose", ["choose"], "Select specific keypaths", "Selection"),
            ("create", ["create", "add", "c", "a"], "Create new fields", "Transformation"),
            ("remove", ["remove", "r"], "Remove keypaths", "Transformation"),
            ("extract", ["extract", "e"], "Extract data from strings", "Transformation"),
            ("join", ["join"], "Join two queries", "Joining"),
            ("union", ["union"], "Union queries", "Joining"),
            ("count", ["count"], "Count events", "Aggregation"),
            ("countby", ["countby"], "Count events by groups", "Aggregation"),
            ("distinct", ["distinct"], "Get distinct values", "Aggregation"),
            ("convert", ["convert", "conv"], "Convert data types", "Transformation"),
            ("replace", ["replace"], "Replace field values", "Transformation"),
            ("move", ["move", "m"], "Move fields", "Transformation"),
            ("redact", ["redact"], "Redact sensitive data", "Security"),
            ("explode", ["explode"], "Explode arrays into documents", "Transformation"),
            ("enrich", ["enrich"], "Enrich with lookup tables", "Enrichment"),
            ("dedupeby", ["dedupeby"], "Deduplicate by expressions", "Filtering"),
            ("block", ["block"], "Block events (negation of filter)", "Filtering"),
            ("stitch", ["stitch"], "Zip two datasets", "Joining"),
            ("multigroupby", ["multigroupby"], "Group by multiple sets", "Aggregation"),
            
            # Text search operators
            ("find", ["find", "text"], "Search for text in keypaths", "Text Search"),
            ("lucene", ["lucene"], "Lucene-compatible search", "Text Search"),
            ("wildfind", ["wildfind", "wildtext"], "Search in entire user data", "Text Search"),
            
            # Time-based operators
            ("around", ["around"], "Select events around timestamp", "Time"),
            ("between", ["between"], "Select events between timestamps", "Time"),
            ("last", ["last"], "Select events from last interval", "Time"),
            ("timeshifted", ["timeshifted"], "Time-shifted events", "Time")
        ]
        
        for name, aliases, description, category in operator_patterns:
            # Extract detailed information from the cheat sheet
            operator_section = self._extract_operator_section(content, name)
            
            examples = self._extract_examples_from_section(operator_section)
            syntax = self._extract_syntax_from_section(operator_section)
            parameters = self._extract_parameters_from_section(operator_section)
            
            operator = DataPrimeOperator(
                name=name,
                aliases=aliases,
                description=description,
                syntax=syntax,
                examples=examples,
                category=category,
                parameters=parameters
            )
            self.operators.append(operator)
    
    def _parse_functions(self, content: str) -> None:
        """Parse DataPrime functions from the cheat sheet."""
        
        # Define function categories and their patterns
        function_categories = {
            "String Functions": [
                "contains", "startsWith", "endsWith", "length", "substr", "trim", 
                "toLowerCase", "toUpperCase", "matches", "split", "indexOf"
            ],
            "Number Functions": [
                "abs", "ceil", "floor", "round", "min", "max", "power", "sqrt",
                "random", "randomInt"
            ],
            "Date/Time Functions": [
                "now", "formatTimestamp", "parseTimestamp", "extractTime", 
                "roundTime", "addTime", "diffTime"
            ],
            "Array Functions": [
                "arrayLength", "arrayContains", "arrayAppend", "arrayJoin",
                "cardinality", "inArray"
            ],
            "IP Functions": [
                "ipInRange", "ipInSubnet", "ipPrefix"
            ],
            "UUID Functions": [
                "isUuid", "randomUuid"
            ],
            "Aggregation Functions": [
                "count", "sum", "avg", "min", "max", "percentile", "stddev",
                "distinct_count", "any_value", "collect"
            ]
        }
        
        for category, function_names in function_categories.items():
            category_section = self._extract_section(content, category)
            
            for func_name in function_names:
                func_info = self._extract_function_info(category_section, func_name)
                if func_info:
                    function = DataPrimeFunction(
                        name=func_name,
                        signature=func_info.get("signature", ""),
                        description=func_info.get("description", ""),
                        examples=func_info.get("examples", []),
                        category=category,
                        return_type=func_info.get("return_type", ""),
                        parameters=func_info.get("parameters", [])
                    )
                    self.functions.append(function)
    
    def _parse_examples(self, content: str) -> None:
        """Extract examples organized by category."""
        
        # Pattern to find example code blocks
        example_pattern = r'```(?:sql|dataprime)?\n(.*?)\n```'
        examples = re.findall(example_pattern, content, re.DOTALL)
        
        # Also find inline examples
        inline_pattern = r'Examples?:\s*\n\n(.*?)(?=\n\n|\n[A-Z]|\Z)'
        inline_examples = re.findall(inline_pattern, content, re.DOTALL)
        
        # Categorize examples
        categories = {
            "filtering": ["filter", "where", "block"],
            "aggregation": ["groupby", "aggregate", "count", "sum", "avg"],
            "transformation": ["create", "extract", "convert", "replace"],
            "time": ["last", "between", "around", "formatTimestamp"],
            "text_search": ["find", "lucene", "contains"],
            "joining": ["join", "union", "stitch"]
        }
        
        all_examples = examples + [ex.strip() for ex in inline_examples if ex.strip()]
        
        for example in all_examples:
            if not example or len(example.strip()) < 10:
                continue
                
            example = example.strip()
            categorized = False
            
            for category, keywords in categories.items():
                if any(keyword in example.lower() for keyword in keywords):
                    if category not in self.examples_by_category:
                        self.examples_by_category[category] = []
                    self.examples_by_category[category].append(example)
                    categorized = True
                    break
            
            if not categorized:
                if "general" not in self.examples_by_category:
                    self.examples_by_category["general"] = []
                self.examples_by_category["general"].append(example)
    
    def _extract_section(self, content: str, section_title: str) -> str:
        """Extract a section from the markdown content."""
        pattern = rf'^#{1,3}\s*{re.escape(section_title)}\s*\n(.*?)(?=^#{1,3}\s|\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _extract_operator_section(self, content: str, operator_name: str) -> str:
        """Extract the section for a specific operator."""
        # Try to find the operator section
        patterns = [
            rf'^#{2,4}\s*{re.escape(operator_name)}\s*\n(.*?)(?=^#{1,4}\s|\Z)',
            rf'^{re.escape(operator_name)}\s*\n(.*?)(?=^[a-zA-Z]|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_examples_from_section(self, section: str) -> List[str]:
        """Extract examples from a section."""
        examples = []
        
        # Find code blocks
        code_blocks = re.findall(r'```(?:sql|dataprime)?\n(.*?)\n```', section, re.DOTALL)
        examples.extend([ex.strip() for ex in code_blocks])
        
        # Find inline examples
        example_lines = re.findall(r'^.*(?:source|filter|groupby|aggregate).*$', section, re.MULTILINE)
        examples.extend([ex.strip() for ex in example_lines if ex.strip()])
        
        # Clean and deduplicate
        clean_examples = []
        for example in examples:
            if example and len(example.strip()) > 5 and example.strip() not in clean_examples:
                clean_examples.append(example.strip())
        
        return clean_examples[:5]  # Limit to 5 examples per operator
    
    def _extract_syntax_from_section(self, section: str) -> str:
        """Extract syntax information from a section."""
        # Look for syntax patterns
        syntax_patterns = [
            r'`([^`]*(?:source|filter|groupby|aggregate)[^`]*)`',
            r'^([a-zA-Z_][a-zA-Z0-9_]*\s+<[^>]+>.*?)$'
        ]
        
        for pattern in syntax_patterns:
            match = re.search(pattern, section, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_parameters_from_section(self, section: str) -> List[Dict[str, str]]:
        """Extract parameter information from a section."""
        parameters = []
        
        # Look for parameter descriptions
        param_pattern = r'`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*[-–—]\s*(.+?)(?=\n|$)'
        matches = re.findall(param_pattern, section)
        
        for param_name, description in matches:
            if len(param_name) > 0 and len(description) > 5:
                parameters.append({
                    "name": param_name.strip(),
                    "description": description.strip()[:200]
                })
        
        return parameters[:3]  # Limit to 3 parameters
    
    def _extract_function_info(self, section: str, function_name: str) -> Optional[Dict[str, Any]]:
        """Extract detailed function information."""
        # Find function signature
        signature_pattern = rf'^{re.escape(function_name)}\s*\n(.+?)(?=\n\n|\n[A-Z]|\Z)'
        signature_match = re.search(signature_pattern, section, re.MULTILINE | re.DOTALL)
        
        if not signature_match:
            return None
        
        function_section = signature_match.group(1)
        
        # Extract signature line
        signature_line = re.search(r'^(.+?)\s*$', function_section, re.MULTILINE)
        signature = signature_line.group(1) if signature_line else ""
        
        # Extract description
        desc_pattern = r'\n(.+?)(?=\n\n|Examples?:|Function parameters:|\Z)'
        desc_match = re.search(desc_pattern, function_section, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""
        
        # Extract examples
        examples = self._extract_examples_from_section(function_section)
        
        return {
            "signature": signature,
            "description": description[:200],
            "examples": examples,
            "return_type": self._extract_return_type(signature),
            "parameters": []
        }
    
    def _extract_return_type(self, signature: str) -> str:
        """Extract return type from function signature."""
        # Simple pattern to extract return type
        if ':' in signature:
            parts = signature.split(':')
            if len(parts) > 1:
                return parts[-1].strip()
        return "unknown"

def load_enhanced_knowledge() -> Dict[str, Any]:
    """Load and parse the DataPrime cheat sheet into structured knowledge."""
    parser = DataPrimeCheatSheetParser()
    return parser.parse()

if __name__ == "__main__":
    # Test the parser
    knowledge = load_enhanced_knowledge()
    print(f"Parsed {knowledge['summary']['total_operators']} operators")
    print(f"Parsed {knowledge['summary']['total_functions']} functions")
    print(f"Operator categories: {knowledge['summary']['operator_categories']}")
    print(f"Function categories: {knowledge['summary']['function_categories']}") 