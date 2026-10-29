"""Optional spans that record outcomes without private exception contents."""

from contextlib import contextmanager


@contextmanager
def span(name: str, attributes: dict, *, client: bool = False):
    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind, StatusCode
    except ImportError:
        trace = None
    if trace is None:
        yield None
        return
    # Automatic exception recording would include exception messages and stack traces.
    with trace.get_tracer("interview_prep.llm").start_as_current_span(
        name,
        attributes=attributes,
        kind=SpanKind.CLIENT if client else SpanKind.INTERNAL,
        record_exception=False,
        set_status_on_exception=False,
    ) as current:
        try:
            yield current
        except BaseException as exc:  # Include interrupts without recording exception contents.
            current.set_attribute("error.type", type(exc).__name__)
            current.set_attribute(
                "interview_prep.outcome", "error" if isinstance(exc, Exception) else "interrupted"
            )
            current.set_status(StatusCode.ERROR)
            raise
        else:
            current.set_attribute("interview_prep.outcome", "success")
