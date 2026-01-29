"""Custom exceptions and error handling."""

class PhillyEdgeError(Exception):
    """Base exception for all application errors."""
    pass

class ConfigurationError(PhillyEdgeError):
    """Missing or invalid configuration."""
    pass

class DataSourceError(PhillyEdgeError):
    """Error fetching from external data source."""
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"{source}: {message}")

class ModelError(PhillyEdgeError):
    """Error in model loading or prediction."""
    pass

class PersistenceError(PhillyEdgeError):
    """Error writing to database."""
    pass

class ValidationError(PhillyEdgeError):
    """Data validation failed."""
    pass

# Error aggregation for pipeline
class PipelineErrors:
    """Collect errors during pipeline run without stopping."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def add_error(self, stage: str, error: Exception):
        self.errors.append({'stage': stage, 'error': str(error)})
    
    def add_warning(self, stage: str, message: str):
        self.warnings.append({'stage': stage, 'message': message})
    
    def has_critical_errors(self) -> bool:
        """Check if any errors prevent continuation."""
        critical_stages = {'INIT', 'PERSIST'}
        return any(e['stage'] in critical_stages for e in self.errors)
    
    def summary(self) -> str:
        return f"{len(self.errors)} errors, {len(self.warnings)} warnings"
