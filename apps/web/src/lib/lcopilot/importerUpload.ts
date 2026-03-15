type ImporterFailureToast = {
  title: string;
  description: string;
  variant: 'destructive';
};

export function buildImporterValidationFailureToast(error: any): ImporterFailureToast {
  if (error?.type === 'rate_limit') {
    return {
      title: 'Rate Limit Exceeded',
      description: error?.message || 'Too many requests. Please try again later.',
      variant: 'destructive',
    };
  }

  if (error?.type === 'validation') {
    return {
      title: 'Validation Failed',
      description: error?.message || 'Document validation failed. Please check your files.',
      variant: 'destructive',
    };
  }

  const errorCode = error?.errorCode || error?.error_code || 'unknown';
  return {
    title: 'Validation Failed',
    description:
      errorCode !== 'unknown'
        ? `${error?.message || 'Unable to start validation.'} (${errorCode})`
        : error?.message || 'Unable to start validation. Please try again.',
    variant: 'destructive',
  };
}
