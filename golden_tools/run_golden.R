# Step 2 of the golden pipeline: run Scrucca's original R algorithm on every curve.
#
# Reads tests/data/golden/curves.csv (written by make_curves.py), and for each section
# (ordered by `seq`) does set.seed(1000 + seq) and calls definitiveFunc(depth, hyd_depth)
# from scrucca.R. A section that fails (error or time limit) is recorded as an error
# and the others go on. Only base R is used.
#
# Outputs (tests/data/golden/):
#   r_summary.csv  source_file, section_id, seq, seed, status, error, sparmin, spar1se,
#                  n_iter, n_candidates, n_converged, n_maxima, out_kind
#                  (out_kind = "list_empty": Newton found roots but no maximum, see below)
#   r_folds.csv    source_file, section_id, point_index, fold
#   r_cv.csv       source_file, section_id, spar, df, cv_error, se
#   r_maxima.csv   source_file, section_id, k, x, y
#   r_fitted.csv   source_file, section_id, point_index, x, y, yhat

TIME_LIMIT <- 120  # seconds per section; guards the original while(check) loop

args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- dirname(normalizePath(file_arg))
golden_dir <- normalizePath(file.path(script_dir, "..", "tests", "data", "golden"))

source(file.path(script_dir, "scrucca.R"))

curves <- read.csv(file.path(golden_dir, "curves.csv"), stringsAsFactors = FALSE)
keys <- unique(curves[, c("source_file", "section_id", "seq")])
keys <- keys[order(keys$seq), ]

# Each value on its own, 17 significant digits: exact round-trip to Python floats.
num <- function(v) ifelse(is.na(v), NA, sprintf("%.17g", v))

summary_rows <- list(); folds_rows <- list(); cv_rows <- list()
max_rows <- list(); fit_rows <- list()

for (r in seq_len(nrow(keys))) {
  src <- keys$source_file[r]; sid <- keys$section_id[r]; sq <- keys$seq[r]
  d <- curves[curves$seq == sq, ]
  d <- d[order(d$step), ]
  x <- d$depth; y <- d$hyd_depth
  seed <- 1000 + sq
  set.seed(seed)

  res <- tryCatch({
    # Fresh limit for this section, counted from now.
    setTimeLimit(elapsed = TIME_LIMIT, transient = TRUE)
    log <- capture.output(val <- definitiveFunc(x, y))
    val
  }, error = function(e) e)
  # Always reached (errors are caught above): removes the limit before the next section.
  setTimeLimit(elapsed = Inf)

  if (inherits(res, "error")) {
    msg <- gsub("[\r\n]+", " ", conditionMessage(res))
    cat(sprintf("ERROR %s section %s: %s\n", src, sid, msg))
    summary_rows[[r]] <- data.frame(source_file = src, section_id = sid, seq = sq, seed = seed,
      status = "error", error = msg, sparmin = NA, spar1se = NA, n_iter = NA,
      n_candidates = NA, n_converged = NA, n_maxima = NA, out_kind = NA)
    next
  }

  out <- res[[1]]; cv <- res$cv
  # When Newton converges only to non-maxima, local.max is empty and
  # matrix(sapply(predict(fit, numeric(0)), cbind), ncol = 2) is a 1x2 *list* matrix of
  # numeric(0), not a 0x2 numeric matrix. Kept as returned, but exported as no maxima.
  # (No candidates gives matrix(NA, 0, 2), a logical 0x2 matrix: that is the genuine
  # "no maxima" case, handled by the Python fallback of runAlg.)
  out_kind <- if (is.list(out)) "list_empty" else "matrix"
  if (out_kind == "list_empty") out <- matrix(numeric(0), nrow = 0, ncol = 2)
  summary_rows[[r]] <- data.frame(source_file = src, section_id = sid, seq = sq, seed = seed,
    status = "ok", error = "", sparmin = num(cv$sparmin), spar1se = num(res[[2]]),
    n_iter = res$n_iter, n_candidates = res$n_candidates, n_converged = res$n_converged,
    n_maxima = nrow(out), out_kind = out_kind)

  fold_of <- integer(length(x))
  for (k in seq_along(cv$folds)) fold_of[cv$folds[[k]]] <- k
  folds_rows[[r]] <- data.frame(source_file = src, section_id = sid,
    point_index = seq_along(x), fold = fold_of)

  cv_rows[[r]] <- data.frame(source_file = src, section_id = sid, spar = num(cv$spar),
    df = num(cv$df), cv_error = num(cv$error), se = num(cv$se))

  if (nrow(out) > 0)
    max_rows[[r]] <- data.frame(source_file = src, section_id = sid, k = seq_len(nrow(out)),
      x = num(out[, 1]), y = num(out[, 2]))

  fit_rows[[r]] <- data.frame(source_file = src, section_id = sid, point_index = seq_along(x),
    x = num(x), y = num(y), yhat = num(res$fitted))

  cat(sprintf("ok    %s section %s: spar1se=%.4f, %d maxima, %d loop(s)\n",
              src, sid, res[[2]], nrow(out), res$n_iter))
}

write_rows <- function(rows, name, cols) {
  rows <- Filter(Negate(is.null), rows)
  df <- if (length(rows)) do.call(rbind, rows) else
    setNames(data.frame(matrix(nrow = 0, ncol = length(cols))), cols)
  write.csv(df, file.path(golden_dir, name), row.names = FALSE, quote = TRUE, na = "")
}

write_rows(summary_rows, "r_summary.csv", c("source_file", "section_id", "seq", "seed", "status",
  "error", "sparmin", "spar1se", "n_iter", "n_candidates", "n_converged", "n_maxima", "out_kind"))
write_rows(folds_rows, "r_folds.csv", c("source_file", "section_id", "point_index", "fold"))
write_rows(cv_rows, "r_cv.csv", c("source_file", "section_id", "spar", "df", "cv_error", "se"))
write_rows(max_rows, "r_maxima.csv", c("source_file", "section_id", "k", "x", "y"))
write_rows(fit_rows, "r_fitted.csv", c("source_file", "section_id", "point_index", "x", "y", "yhat"))

cat(R.version.string, "\n")
cat("RNG:", paste(RNGkind(), collapse = ", "), "\n")
