"""Exact deterministic portable item catalog."""

from datetime import UTC, datetime

from app.models.items.responses import Item

_CATALOG = (
    (
        "item-001",
        "Alpha Widget",
        "electronics",
        2999,
        True,
        "2024-01-15T10:30:00",
        "A versatile electronic widget for everyday use",
    ),
    (
        "item-002",
        "Beta Gadget",
        "electronics",
        4999,
        True,
        "2024-01-16T11:00:00",
        "Advanced gadget with smart features",
    ),
    ("item-003", "Gamma Tool", "tools", 1550, False, "2024-01-17T09:15:00", "Precision tool for professional work"),
    (
        "item-004",
        "Delta Component",
        "electronics",
        899,
        True,
        "2024-01-18T14:45:00",
        "Essential component for electronics projects",
    ),
    (
        "item-005",
        "Epsilon Sensor",
        "electronics",
        3499,
        True,
        "2024-01-19T08:00:00",
        "High-precision environmental sensor",
    ),
    ("item-006", "Zeta Cable", "accessories", 1299, True, "2024-01-20T16:30:00", "Premium quality data cable"),
    ("item-007", "Eta Adapter", "accessories", 999, False, "2024-01-21T10:00:00", "Universal power adapter"),
    ("item-008", "Theta Board", "electronics", 8999, True, "2024-01-22T11:30:00", "Development board for prototyping"),
    ("item-009", "Iota Switch", "electronics", 599, True, "2024-01-23T09:45:00", "Tactile push button switch"),
    ("item-010", "Kappa Display", "electronics", 4599, True, "2024-01-24T13:00:00", "OLED display module"),
    ("item-011", "Lambda Motor", "robotics", 2499, True, "2024-01-25T08:30:00", "DC motor for robotics projects"),
    ("item-012", "Mu Servo", "robotics", 1899, False, "2024-01-26T15:00:00", "High-torque servo motor"),
    ("item-013", "Nu Battery", "power", 1499, True, "2024-01-27T10:15:00", "Rechargeable lithium battery pack"),
    ("item-014", "Xi Charger", "power", 2299, True, "2024-01-28T11:45:00", "Smart battery charger"),
    ("item-015", "Omicron Relay", "electronics", 799, True, "2024-01-29T09:00:00", "5V relay module"),
    ("item-016", "Pi Controller", "electronics", 5599, True, "2024-01-30T14:30:00", "Microcontroller board"),
    ("item-017", "Rho Resistor Kit", "components", 1199, True, "2024-02-01T08:00:00", "Assorted resistor pack"),
    (
        "item-018",
        "Sigma Capacitor Set",
        "components",
        1399,
        True,
        "2024-02-02T10:30:00",
        "Electrolytic capacitor assortment",
    ),
    ("item-019", "Tau LED Pack", "components", 699, True, "2024-02-03T11:00:00", "Multi-color LED assortment"),
    ("item-020", "Upsilon Wire Set", "accessories", 899, False, "2024-02-04T09:15:00", "Jumper wire kit"),
    ("item-021", "Phi Breadboard", "tools", 499, True, "2024-02-05T13:45:00", "Solderless breadboard"),
    (
        "item-022",
        "Chi Soldering Iron",
        "tools",
        3599,
        True,
        "2024-02-06T10:00:00",
        "Temperature-controlled soldering station",
    ),
    ("item-023", "Psi Multimeter", "tools", 4299, True, "2024-02-07T11:30:00", "Digital multimeter with auto-ranging"),
    ("item-024", "Omega Oscilloscope", "tools", 29999, True, "2024-02-08T14:00:00", "Portable digital oscilloscope"),
    (
        "item-025",
        "Alpha Pro Widget",
        "electronics",
        5999,
        True,
        "2024-02-09T08:30:00",
        "Professional-grade widget with extended features",
    ),
    ("item-026", "Beta Max Gadget", "electronics", 7999, False, "2024-02-10T09:00:00", "Maximum performance gadget"),
    ("item-027", "Gamma Plus Tool", "tools", 2599, True, "2024-02-11T10:15:00", "Enhanced precision tool"),
    ("item-028", "Delta Ultra Component", "electronics", 1699, True, "2024-02-12T11:45:00", "Ultra-reliable component"),
    ("item-029", "Epsilon HD Sensor", "electronics", 5499, True, "2024-02-13T13:00:00", "High-definition sensor array"),
    ("item-030", "Zeta Premium Cable", "accessories", 1999, True, "2024-02-14T15:30:00", "Gold-plated premium cable"),
)

MOCK_ITEMS: list[Item] = [
    Item.model_validate(
        {
            "id": item_id,
            "name": name,
            "category": category,
            "price": {"amountMinor": amount_minor, "currency": "USD"},
            "inStock": in_stock,
            "createdAt": datetime.fromisoformat(created_at).replace(tzinfo=UTC),
            "description": description,
        }
    )
    for item_id, name, category, amount_minor, in_stock, created_at, description in _CATALOG
]
