import { Router, type IRouter } from "express";
import healthRouter from "./health";
import inspectionRouter from "./inspection";
import candidateListingsRouter from "./candidate-listings";
import tokenSafetyRouter from "./token-safety";
import opportunityEvaluationRouter from "./opportunity-evaluation";

const router: IRouter = Router();

router.use(healthRouter);
router.use(inspectionRouter);
router.use(candidateListingsRouter);
router.use(tokenSafetyRouter);
router.use(opportunityEvaluationRouter);

export default router;
