package ke.co.kenyadatarights

fun verifiedUserLabel(
    sourceKind: String,
    classificationCount: Int,
    selected: LoanMessageLabel?,
): LoanMessageLabel? =
    if (sourceKind == "shared_text" && classificationCount == 1) selected else null
