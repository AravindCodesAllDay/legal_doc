import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { cn } from "../../utils/cn";

interface GlassCardProps {
    children: ReactNode;
    className?: string;
    hoverEffect?: boolean;
}

export const GlassCard = ({ children, className, hoverEffect = false }: GlassCardProps) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={cn(
                "backdrop-blur-md bg-glass-bg border border-glass-border rounded-2xl p-6 shadow-xl",
                hoverEffect && "hover:bg-white/5 transition-colors duration-200",
                className
            )}
        >
            {children}
        </motion.div>
    );
};
