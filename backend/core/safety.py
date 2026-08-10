"""Safe-default operational state for services and future workers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyStatus:
    """A snapshot of the boundary that controls activity."""

    watchdog_healthy: bool
    kill_switch_active: bool
    action_allowed: bool
    reason: str


class SafetyBoundary:
    """Small, fail-closed boundary for future service/worker activity.

    The default state permits no action. This foundation does not implement
    trading shutdown behavior; it only provides a safe place for future
    components to check whether activity is allowed.
    """

    def __init__(
        self,
        *,
        watchdog_healthy: bool = False,
        kill_switch_active: bool = True,
        reason: str = "safe_default",
    ) -> None:
        self.watchdog_healthy = watchdog_healthy
        self.kill_switch_active = kill_switch_active
        self.reason = reason

    @property
    def action_allowed(self) -> bool:
        """Return whether a future component may perform activity."""

        return self.watchdog_healthy and not self.kill_switch_active

    def status(self) -> SafetyStatus:
        """Return an immutable safety snapshot."""

        return SafetyStatus(
            watchdog_healthy=self.watchdog_healthy,
            kill_switch_active=self.kill_switch_active,
            action_allowed=self.action_allowed,
            reason=self.reason,
        )

    def check_activity(self) -> bool:
        """Return the fail-closed activity decision."""

        return self.action_allowed

    def activate_kill_switch(self, reason: str = "kill_switch_active") -> None:
        """Prevent future activity until the boundary is explicitly reset."""

        self.kill_switch_active = True
        self.reason = reason

    def set_watchdog_health(self, healthy: bool, reason: str | None = None) -> None:
        """Update watchdog state without implicitly enabling activity."""

        self.watchdog_healthy = healthy
        if reason is not None:
            self.reason = reason

    def release_kill_switch(self, reason: str = "safety_checks_passed") -> None:
        """Release the switch only after an independent watchdog is healthy."""

        if not self.watchdog_healthy:
            self.reason = "watchdog_unhealthy"
            return
        self.kill_switch_active = False
        self.reason = reason