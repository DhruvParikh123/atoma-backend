import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class BookingConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Booking conflict detected. Time slot not available.'
    default_code = 'booking_conflict'


class BeauticianNotAvailableError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Beautician is not available at the requested time.'
    default_code = 'beautician_not_available'


class InvalidBookingStatusError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid booking status transition.'
    default_code = 'invalid_status_transition'


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent API error responses."""
    
    # Log the exception
    logger.error(
        f"Exception occurred: {exc.__class__.__name__}: {str(exc)}",
        extra={
            'view': context.get('view'),
            'request': context.get('request'),
            'exception': exc
        }
    )
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Add error code to response
        if hasattr(exc, 'default_code'):
            response.data['code'] = exc.default_code
        
        # Wrap errors in a consistent format
        if 'detail' in response.data:
            response.data = {
                'success': False,
                'error': {
                    'code': response.data.get('code', 'error'),
                    'message': response.data['detail'],
                    'details': {}
                }
            }
        else:
            # Handle field errors
            errors = {}
            for field, error_list in response.data.items():
                if isinstance(error_list, list):
                    errors[field] = [str(e) for e in error_list]
                else:
                    errors[field] = str(error_list)
            
            response.data = {
                'success': False,
                'error': {
                    'code': 'validation_error',
                    'message': 'Validation failed',
                    'details': errors
                }
            }
        
        return response
    
    # Handle Django validation errors
    if isinstance(exc, ValidationError):
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'validation_error',
                    'message': 'Validation failed',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle object does not exist
    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': 'Resource not found',
                    'details': {}
                }
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Log unexpected errors
    logger.exception("Unexpected error occurred")
    
    return Response(
        {
            'success': False,
            'error': {
                'code': 'internal_error',
                'message': 'An unexpected error occurred',
                'details': {}
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
