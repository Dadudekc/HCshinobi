import { NextFunction, Request, Response } from 'express';

import authService from '../services/auth.service';

export interface AuthenticatedRequest extends Request {
  user?: {
    userId: string;
    role: string;
  };
}

export const authenticate = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader) {
      res.status(401).json({ error: 'No token provided' });
      return;
    }

    const token = authHeader.split(' ')[1];

    if (!token) {
      res.status(401).json({ error: 'Invalid token format' });
      return;
    }

    const payload = authService.verifyToken(token);
    req.user = payload;

    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

export const authorize = (roles: string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }

    if (!roles.includes(req.user.role)) {
      res.status(403).json({ error: 'Forbidden' });
      return;
    }

    next();
  };
};

export const requireAuth = [authenticate];

export const requireAdmin = [authenticate, authorize(['admin'])];

export const requireAgent = [authenticate, authorize(['agent'])];

export const requireUser = [authenticate, authorize(['user'])];

export const requireAuthOrAgent = [
  authenticate,
  (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (req.user?.role === 'agent' || req.user?.role === 'user') {
      next();
    } else {
      res.status(403).json({ error: 'Forbidden' });
    }
  },
]; 