

def tol_check(ref, compare, min_error=0.05, low_val_correction=3.0):
    """Tolerance check

    The tolerance check is very simple. In essence it checks to ensure
    that the ``compare`` value is within ``min_error`` percentage of the ``ref`` value.
    However there are special conditions.

    If the ref value is zero == the compare value we will alwys return True to avoid
    calculation overhead.

    If the ref value is zero we check if the compare value is below the low_val_correction
    threshold.

    The low value correction is also used if ref is small. In this case, if one minus the
    difference of the ref and low value correction / reference value yields greater error
    correction, then this is used.

    For example, if the reference was 1 and the compare was 2, with a min_error set to the
    default, the tolerance check would return False. At low values this is probably undesirable
    and so, the low_val_correction allows for a greater amount of error at low values.
    As an example, with the lvc set to 3, the allowe error would be much higher, allowing the
    tolerance check to pass.

    The lvc will only take effect if the error it produces is greater than the ``min_error``.

    Args:
        ref: The reference value
        compare: The comparison value
        min_error: The minimum allowed error
        low_val_correction: A correction value for lower values
    """
    if ref == compare:
        return True, min_error
    elif ref == 0:
        return compare <= low_val_correction, low_val_correction
    else:
        compared_value = float(compare)
        reference_value = float(ref)
        relational_error = 1.0 - ((reference_value - low_val_correction) / reference_value)
        tolerance = max([relational_error, min_error])
        difference = abs(reference_value - compared_value)
        difference_error = difference / reference_value
        return difference_error <= tolerance, tolerance
