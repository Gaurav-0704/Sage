// Shared school constants for the frontend.
// One source of truth for class ordering — used by every dropdown / table.

export const CLASS_ORDER = ["KG1","KG2","1","2","3","4","5","6","7","8","9","10"];

export const classSortKey = (c) => {
  const i = CLASS_ORDER.indexOf(c);
  return i < 0 ? CLASS_ORDER.length : i;
};

export const SUBJECTS = ["English", "Hindi", "Math", "Science", "Social"];
export const EXPENSE_CATEGORIES = ["salary", "utilities", "supplies",
                                    "maintenance", "transport", "other"];
