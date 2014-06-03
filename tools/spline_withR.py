""" 
# R script for computing the local(s) maxima of y = f(x) with f() estimated
# by smooth.spline using the smoothing parameter selected by 1se-rule from 
# 10-fold CV  
#
# Input: vectors x and y
# Output: a matrix of (x,y) values at each local maxima
#
# Author: Luca Scrucca (26/3/2014)
"""

import rpy2.robjects as robjects


import numpy as np

def runAlg(depts,HydDept):
    HydDept = np.array(HydDept)
    depts = np.array(depts)
    y = robjects.FloatVector(HydDept)
    x = robjects.FloatVector(depts)
    robjects.r('''
            definitiveFunc <- function(x,y)
            {            
            cv.smooth.spline <- function (x, y, nfold = 10, ngrid = 100, 
                                          spar = log(seq(1, exp(1), length = ngrid)),
                                          plot = TRUE, log.axes = "y", ...) 
            {
              x <- as.vector(x)
              y <- as.vector(y)
              n <- length(y)
              if(length(x) != n)
                stop("'x' and 'y' lengths differ")  
              xfolds <- folds(n, nfold)
              ngrid <- length(spar)
              err <- df <- matrix(as.double(NA), ngrid, nfold)
              for(i in 1:nfold) 
                 { for(s in 1:ngrid)
                      { mod <- smooth.spline(x[-xfolds[[i]]], y[-xfolds[[i]]], spar = spar[s])
                        df[s,i] <- mod$df
                        err[s,i] <- sum((y[xfolds[[i]]] - predict(mod, x[xfolds[[i]]])$y)^2)
                 }
              }
              df <- rowMeans(df)
              cv.error <- rowSums(err)/n
              folds.size <- sapply(xfolds, length)
              err <- sweep(err, 2, FUN="/", STATS=folds.size)
              se <- apply(err, 1, function(e) sqrt(var(e)/nfold))
              est <- spar[which.min(cv.error)]
              oneserule <- (cv.error+se)[which.min(cv.error)]
              i <- which(cv.error[which(spar >= est)] <= oneserule)[1]
              est1se <- spar[spar >= est][i]
              
              if(plot)
                { oldpar <- par(no.readonly = TRUE)
                  on.exit(par(oldpar))
                  par(mar = pmax(oldpar$mar, c(4,4,4,1)))
                  plot(spar, cv.error, type = "n", 
                       log = log.axes, xaxt = "n",
                       ylim = range(c(cv.error-se, cv.error+se)),
                       xlab = "Smoothing parameter (spar)")
                  at1 <- seq((min(spar)%/%0.1*0.1), (max(spar)%/%0.1*0.1), by = 0.1)
                  axis(side = 1, at = at1)
                  labels3 <- c(round(min(df)), 
                               seq((min(df)%/%10*10), (max(df)%/%10)*10, by = 10),
                               round(max(df)))
                  at3 <- predict(smooth.spline(df,spar),labels3)$y
                  axis(side = 3, at = at3, labels = labels3)
                  mtext("Equivalent degrees of freedom", side = 3, line = 2.5, cex=par("cex"))
                  segments(spar, cv.error-se, spar, cv.error+se, 
                           col = "lightgrey", lwd = 2)
                  lines(spar, cv.error, type = "o", pch = 20, lty = 1)
                  abline(v = est, lty = 2)
                  abline(h = (cv.error+se)[which.min(cv.error)], lty = 2)
                  abline(v = est1se, lty = 3)
              }  
              
              return(list(spar = spar, df = df, 
                          error = cv.error, se = se, 
                          sparmin = est, spar1se = est1se))
            }
    
    
    
            folds <- function (n, k, balanced = TRUE) 
            {
              fold <- if(balanced) sample(rep(1:k, length = n), n, replace = FALSE)
                      else         sample(k, n, replace = TRUE)
              folds <- vector("list", length = k)
              for(i in 1:k)
                 { folds[[i]] <- which(fold == i) }
              return(folds)
            }
        
            newtonraphson <- function (ftn, x0, tol = 0.000000001, max.iter = 100) 
            {
            # Newton-Raphson algorithm to find x such that ftn(x)[1] == 0.
              x <- x0
              fx <- ftn(x)
              iter <- 0
              while((abs(fx[1]) > tol) && (iter < max.iter)) 
                { x <- x - fx[1]/fx[2]
                  fx <- ftn(x)
                  iter <- iter + 1
                  cat("At iteration", iter, "value of x is:", x, "\n")
              }
              if(abs(fx[1]) > tol) 
                { cat("Algorithm failed to converge\n")
                  return(NA)
              }
              else { cat("Algorithm converged\n")
                     return(x)
              }
            }
            
            f <- function(x) 
            { # returns function value and its derivative at x
              f1x <- predict(fit, x, deriv=1)$y
              f2x <- predict(fit, x, deriv=2)$y
              return(c(f1x, f2x))
            }
               
            # check for convergence for newtonraphson method  
            check=TRUE
            while (check)
            {
              cv = cv.smooth.spline(x, y,plot=F)
              fit = smooth.spline(x, y, spar = cv$spar1se)
              # fit = smooth.spline(x, y, spar = cv$sparmin)
              # plot(fit)
              fderiv1 = predict(fit, deriv = 1)
              # plot(fderiv1)
              # stationary points
              candidates = x[which(diff(sign(fderiv1$y)) != 0)]
              
              if(length(candidates) > 0)
              { xsol = rep(NA, length(candidates))
                for(i in 1:length(candidates))
                { xsol[i] = newtonraphson(f, candidates[i], tol = 1e-09) }
                xsol=xsol[!is.na(xsol)]
                if(length(xsol)>0)
                {
                  local.max = xsol[which(predict(fit, xsol, deriv=2)$y < 0)]
                  out = matrix(sapply(predict(fit, local.max), cbind), ncol = 2)
                  check=FALSE
                }   
              } else 
              { 
                out = matrix(NA, nrow = 0, ncol = 2) 
                check=FALSE
              }
            }
            

            # out is a matrix of (x,y) values at each local maxima
            return(list(out,cv$spar1se))
            }
            
            ''')
    
    
    definitiveFunc = robjects.globalenv['definitiveFunc']
    #converto gli array python in vettori R
    out,spar = definitiveFunc(x,y)
    
    if type(out) == robjects.vectors.FloatVector:
        return [out[0]] , [out[1]], spar[0]
    else:
        if len(out) > 0:
            return list(out.rx(True,1)) , list(out.rx(True,2)) , spar[0]
        else:
            return [x[-1]],[y[-1]] , spar[0]
    
    
